from fastapi import FastAPI, Query, Response, status, HTTPException
from pydantic import BaseModel, Field

app = FastAPI()

# ══ PYDANTIC MODELS ═══════════════════════════════════════

class OrderRequest(BaseModel):
    customer_name: str = Field(..., min_length=2, max_length=100)
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0, le=100)
    delivery_address: str = Field(..., min_length=10)


class NewProduct(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    price: int = Field(..., gt=0)
    category: str = Field(..., min_length=2)
    in_stock: bool = True


class CheckoutRequest(BaseModel):
    customer_name: str = Field(..., min_length=2)
    delivery_address: str = Field(..., min_length=10)


# ══ DATA STORAGE ══════════════════════════════════════════

products = [
    {"id": 1, "name": "Wireless Mouse", "price": 499, "category": "Electronics", "in_stock": True},
    {"id": 2, "name": "Notebook", "price": 99, "category": "Stationery", "in_stock": True},
    {"id": 3, "name": "USB Hub", "price": 799, "category": "Electronics", "in_stock": False},
    {"id": 4, "name": "Pen Set", "price": 49, "category": "Stationery", "in_stock": True},
]

orders = []
cart = []
order_counter = 1


# ══ HELPER FUNCTIONS ══════════════════════════════════════

def find_product(product_id: int):
    for p in products:
        if p["id"] == product_id:
            return p
    return None


def calculate_total(product: dict, quantity: int):
    return product["price"] * quantity


def calculate_cart_total():
    return sum(item["subtotal"] for item in cart)


def filter_products_logic(category=None, min_price=None, max_price=None, in_stock=None):

    result = products

    if category:
        result = [p for p in result if p["category"].lower() == category.lower()]

    if min_price is not None:
        result = [p for p in result if p["price"] >= min_price]

    if max_price is not None:
        result = [p for p in result if p["price"] <= max_price]

    if in_stock is not None:
        result = [p for p in result if p["in_stock"] == in_stock]

    return result


# ══ ROOT ══════════════════════════════════════════════════

@app.get("/")
def home():
    return {"message": "Welcome to our E-commerce API 🚀"}


# ══ PRODUCT APIs ══════════════════════════════════════════

@app.get("/products")
def get_all_products():
    return {"products": products, "total": len(products)}


@app.get("/products/filter")
def filter_products(
    category: str = Query(None),
    min_price: int = Query(None),
    max_price: int = Query(None),
    in_stock: bool = Query(None),
):

    result = filter_products_logic(category, min_price, max_price, in_stock)

    return {
        "filtered_products": result,
        "count": len(result)
    }


@app.get("/products/{product_id}")
def get_product(product_id: int):

    product = find_product(product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return {"product": product}


@app.post("/products")
def add_product(new_product: NewProduct, response: Response):

    next_id = max([p["id"] for p in products], default=0) + 1

    product = {
        "id": next_id,
        "name": new_product.name,
        "price": new_product.price,
        "category": new_product.category,
        "in_stock": new_product.in_stock,
    }

    products.append(product)

    response.status_code = status.HTTP_201_CREATED

    return {"message": "Product added successfully", "product": product}


@app.put("/products/{product_id}")
def update_product(
    product_id: int,
    in_stock: bool = Query(None),
    price: int = Query(None),
):

    product = find_product(product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if in_stock is not None:
        product["in_stock"] = in_stock

    if price is not None:

        if price <= 0:
            raise HTTPException(status_code=400, detail="Price must be greater than 0")

        product["price"] = price

    return {"message": "Product updated successfully", "product": product}


@app.delete("/products/{product_id}")
def delete_product(product_id: int):

    product = find_product(product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    products.remove(product)

    return {"message": f"Product '{product['name']}' deleted successfully"}


# ══ COMPARE PRODUCTS ══════════════════════════════════════

@app.get("/products/compare")
def compare_products(
    product_id_1: int = Query(...),
    product_id_2: int = Query(...),
):

    p1 = find_product(product_id_1)
    p2 = find_product(product_id_2)

    if not p1:
        raise HTTPException(status_code=404, detail=f"Product {product_id_1} not found")

    if not p2:
        raise HTTPException(status_code=404, detail=f"Product {product_id_2} not found")

    cheaper = p1 if p1["price"] < p2["price"] else p2

    return {
        "product_1": p1,
        "product_2": p2,
        "better_value": cheaper["name"],
        "price_difference": abs(p1["price"] - p2["price"]),
    }


# ══ ORDER APIs ════════════════════════════════════════════

@app.post("/orders")
def place_order(order_data: OrderRequest):

    global order_counter

    product = find_product(order_data.product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if not product["in_stock"]:
        raise HTTPException(status_code=400, detail=f"{product['name']} is out of stock")

    total = calculate_total(product, order_data.quantity)

    order = {
        "order_id": order_counter,
        "customer_name": order_data.customer_name,
        "product": product["name"],
        "quantity": order_data.quantity,
        "delivery_address": order_data.delivery_address,
        "total_price": total,
        "status": "confirmed",
    }

    orders.append(order)
    order_counter += 1

    return {"message": "Order placed successfully", "order": order}


@app.get("/orders")
def get_all_orders():

    if not orders:
        return {"message": "No new order added"}

    return {
        "orders": orders,
        "total_orders": len(orders)
    }

# ══ CART SYSTEM ═══════════════════════════════════════════

@app.post("/cart/add")
def add_to_cart(
    product_id: int = Query(...),
    quantity: int = Query(1),
):

    product = find_product(product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if not product["in_stock"]:
        raise HTTPException(status_code=400, detail=f"{product['name']} is out of stock")

    if quantity < 1:
        raise HTTPException(status_code=400, detail="Quantity must be at least 1")

    for item in cart:
        if item["product_id"] == product_id:

            item["quantity"] += quantity
            item["subtotal"] = calculate_total(product, item["quantity"])

            return {"message": "Cart updated", "cart_item": item}

    cart_item = {
        "product_id": product_id,
        "product_name": product["name"],
        "quantity": quantity,
        "unit_price": product["price"],
        "subtotal": calculate_total(product, quantity),
    }

    cart.append(cart_item)

    return {"message": "Added to cart", "cart_item": cart_item}


@app.get("/cart")
def view_cart():

    if not cart:
        return {
            "message": "Cart is empty",
            "items": [],
            "grand_total": 0
        }

    return {
        "items": cart,
        "item_count": len(cart),
        "grand_total": calculate_cart_total(),
    }


# ══ CHECKOUT ══════════════════════════════════════════════

@app.post("/cart/checkout")
def checkout(checkout_data: CheckoutRequest):

    global order_counter

    if not cart:
        raise HTTPException(status_code=400, detail="Cart is empty — add items first")

    placed_orders = []
    grand_total = 0

    for item in cart:

        order = {
            "order_id": order_counter,
            "customer_name": checkout_data.customer_name,
            "product": item["product_name"],
            "quantity": item["quantity"],
            "delivery_address": checkout_data.delivery_address,
            "total_price": item["subtotal"],
            "status": "confirmed",
        }

        orders.append(order)
        placed_orders.append(order)

        grand_total += item["subtotal"]
        order_counter += 1

    # IMPORTANT → CLEAR CART AFTER CHECKOUT
    cart.clear()

    return {
        "message": "Checkout successful",
        "orders_placed": placed_orders,
        "grand_total": grand_total,
    }


# ══ REMOVE ITEM FROM CART ═════════════════════════════════

@app.delete("/cart/{product_id}")
def remove_from_cart(product_id: int):

    for item in cart:
        if item["product_id"] == product_id:
            cart.remove(item)
            return {"message": f"{item['product_name']} removed from cart"}

    raise HTTPException(status_code=404, detail="Product not in cart")
