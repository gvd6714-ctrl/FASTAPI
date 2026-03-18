from fastapi import FastAPI, Query, Response, status
from pydantic import BaseModel, Field

app = FastAPI()

# ===================== MODELS =====================

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

# ===================== DATA =====================

products = [
    {'id': 1, 'name': 'Wireless Mouse', 'price': 499, 'category': 'Electronics', 'in_stock': True},
    {'id': 2, 'name': 'Notebook', 'price': 99, 'category': 'Stationery', 'in_stock': True},
    {'id': 3, 'name': 'USB Hub', 'price': 799, 'category': 'Electronics', 'in_stock': False},
    {'id': 4, 'name': 'Pen Set', 'price': 49, 'category': 'Stationery', 'in_stock': True},
]

orders = []
order_counter = 1
cart = []

# ===================== HELPERS =====================

def find_product(product_id: int):
    for p in products:
        if p['id'] == product_id:
            return p
    return None

def calculate_total(product: dict, quantity: int):
    return product['price'] * quantity

def filter_products_logic(category=None, min_price=None, max_price=None, in_stock=None):
    result = products
    if category is not None:
        result = [p for p in result if p['category'] == category]
    if min_price is not None:
        result = [p for p in result if p['price'] >= min_price]
    if max_price is not None:
        result = [p for p in result if p['price'] <= max_price]
    if in_stock is not None:
        result = [p for p in result if p['in_stock'] == in_stock]
    return result

# ===================== ROUTES =====================

@app.get('/')
def home():
    return {'message': 'Welcome to our E-commerce API'}

@app.get('/products')
def get_all_products():
    return {'products': products, 'total': len(products)}

# ===================== Q5 =====================
@app.get('/products/sort-by-category')
def sort_by_category():
    result = sorted(products, key=lambda p: (p['category'], p['price']))
    return {'products': result, 'total': len(result)}

# ===================== Q1 =====================
@app.get('/products/filter')
def filter_products(category: str = Query(None), min_price: int = Query(None),
                    max_price: int = Query(None), in_stock: bool = Query(None)):
    result = filter_products_logic(category, min_price, max_price, in_stock)
    return {'filtered_products': result, 'count': len(result)}

# ===================== Q2 =====================
@app.get('/products/compare')
def compare_products(product_id_1: int = Query(...), product_id_2: int = Query(...)):
    p1 = find_product(product_id_1)
    p2 = find_product(product_id_2)

    if not p1 or not p2:
        return {'error': 'Product not found'}

    cheaper = p1 if p1['price'] < p2['price'] else p2

    return {
        'product_1': p1,
        'product_2': p2,
        'better_value': cheaper['name'],
        'price_diff': abs(p1['price'] - p2['price'])
    }

# ===================== Q3 =====================
@app.get('/products/search')
def search_products(keyword: str = Query(...)):
    results = [p for p in products if keyword.lower() in p['name'].lower()]
    if not results:
        return {'message': f'No products found for: {keyword}'}
    return {'results': results, 'total_found': len(results)}

# ===================== Q6 =====================
@app.get('/products/browse')
def browse_products(
    keyword: str = Query(None),
    sort_by: str = Query('price'),
    order: str = Query('asc'),
    page: int = Query(1, ge=1),
    limit: int = Query(4, ge=1, le=20),
):
    result = products
    if keyword:
        result = [p for p in result if keyword.lower() in p['name'].lower()]
    if sort_by in ['price', 'name']:
        result = sorted(result, key=lambda p: p[sort_by], reverse=(order == 'desc'))

    total = len(result)
    start = (page - 1) * limit
    paged = result[start:start + limit]

    return {
        'keyword': keyword,
        'sort_by': sort_by,
        'order': order,
        'page': page,
        'limit': limit,
        'total_found': total,
        'total_pages': -(-total // limit),
        'products': paged
    }

@app.get('/products/sort')
def sort_products(sort_by: str = Query('price'), order: str = Query('asc')):
    reverse = True if order == 'desc' else False
    sorted_products = sorted(products, key=lambda p: p[sort_by], reverse=reverse)
    return {'products': sorted_products}

@app.get('/products/page')
def pagination(page: int = Query(1), limit: int = Query(2)):
    start = (page - 1) * limit
    return {'products': products[start:start + limit]}

@app.post('/products')
def add_product(new_product: NewProduct):
    new_id = max(p['id'] for p in products) + 1
    product = new_product.dict()
    product['id'] = new_id
    products.append(product)
    return {'message': 'Product added', 'product': product}

@app.put('/products/{product_id}')
def update_product(product_id: int, in_stock: bool = Query(None), price: int = Query(None)):
    product = find_product(product_id)
    if not product:
        return {'error': 'Product not found'}
    if in_stock is not None:
        product['in_stock'] = in_stock
    if price is not None:
        product['price'] = price
    return {'message': 'Updated', 'product': product}

@app.delete('/products/{product_id}')
def delete_product(product_id: int):
    product = find_product(product_id)
    if not product:
        return {'error': 'Product not found'}
    products.remove(product)
    return {'message': 'Product deleted'}

@app.get('/products/{product_id}')
def get_product(product_id: int):
    product = find_product(product_id)
    if not product:
        return {'error': 'Product not found'}
    return product

@app.post('/orders')
def place_order(order: OrderRequest):
    global order_counter
    product = find_product(order.product_id)
    if not product:
        return {'error': 'Product not found'}

    total = calculate_total(product, order.quantity)

    new_order = {
        'order_id': order_counter,
        'customer_name': order.customer_name,
        'product': product['name'],
        'quantity': order.quantity,
        'total_price': total
    }

    orders.append(new_order)
    order_counter += 1

    return {'message': 'Order placed', 'order': new_order}

@app.get('/orders')
def get_orders():
    return {'orders': orders, 'total_orders': len(orders)}

# ===================== BONUS =====================
@app.get('/orders/page')
def get_orders_paged(
    page: int = Query(1, ge=1),
    limit: int = Query(3, ge=1, le=20),
):
    start = (page - 1) * limit
    return {
        'page': page,
        'limit': limit,
        'total': len(orders),
        'total_pages': -(-len(orders) // limit),
        'orders': orders[start:start + limit],
    }

# ===================== Q4 =====================
@app.get('/orders/search')
def search_orders(customer_name: str = Query(...)):
    results = [o for o in orders if customer_name.lower() in o['customer_name'].lower()]
    if not results:
        return {'message': f'No orders found for: {customer_name}'}
    return {'customer_name': customer_name, 'total_found': len(results), 'orders': results}

@app.delete('/orders/{order_id}')
def delete_order(order_id: int):
    for o in orders:
        if o['order_id'] == order_id:
            orders.remove(o)
            return {'message': 'Order deleted'}
    return {'error': 'Order not found'}

@app.post('/cart/add')
def add_to_cart(product_id: int = Query(...), quantity: int = Query(1)):
    product = find_product(product_id)
    if not product:
        return {'error': 'Product not found'}

    cart.append({
        'product_id': product_id,
        'name': product['name'],
        'quantity': quantity,
        'price': product['price']
    })

    return {'message': 'Added to cart'}

@app.get('/cart')
def view_cart():
    return {'cart': cart}

@app.post('/cart/checkout')
def checkout():
    if not cart:
        return {'error': 'Cart is empty'}
    cart.clear()
    return {'message': 'Checkout successful'}

@app.delete('/cart/{product_id}')
def delete_cart_item(product_id: int):
    for item in cart:
        if item['product_id'] == product_id:
            cart.remove(item)
            return {'message': 'Item removed'}
    return {'error': 'Product not in cart'}