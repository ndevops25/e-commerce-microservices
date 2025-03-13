# app.py - Microserviço de Produtos
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

# Inicialização da aplicação Flask
app = Flask(__name__)

# Configuração do banco de dados
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///products.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Modelo de dados - Produto
class Product(db.Model):
    """
    Modelo para a tabela de produtos
    """
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    category_id = db.Column(db.String(36), nullable=False)
    supplier_id = db.Column(db.String(36), nullable=False)
    features = db.Column(db.JSON, nullable=True)
    images = db.Column(db.JSON, nullable=True)  # Lista de URLs
    status = db.Column(db.String(20), nullable=False, default='active')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    sku = db.Column(db.String(50), nullable=False, unique=True)

# Modelo de dados - Histórico de Preços
class PriceHistory(db.Model):
    """
    Modelo para a tabela de histórico de preços
    """
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.String(36), db.ForeignKey('product.id'), nullable=False)
    previous_price = db.Column(db.Float, nullable=False)
    new_price = db.Column(db.Float, nullable=False)
    change_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    reason = db.Column(db.String(255), nullable=True)

# Criação das tabelas no banco de dados
with app.app_context():
    db.create_all()

# Rotas do microserviço

@app.route('/products', methods=['GET'])
def get_all_products():
    """
    Retorna todos os produtos
    """
    products = Product.query.all()
    return jsonify([{
        'id': product.id,
        'name': product.name,
        'price': product.price,
        'stock': product.stock,
        'category_id': product.category_id,
        'supplier_id': product.supplier_id,
        'status': product.status
    } for product in products])

@app.route('/products/<product_id>', methods=['GET'])
def get_product(product_id):
    """
    Retorna um produto específico pelo ID
    """
    product = Product.query.get_or_404(product_id)
    return jsonify({
        'id': product.id,
        'name': product.name,
        'description': product.description,
        'price': product.price,
        'stock': product.stock,
        'category_id': product.category_id,
        'supplier_id': product.supplier_id,
        'features': product.features,
        'images': product.images,
        'status': product.status,
        'sku': product.sku,
        'created_at': product.created_at,
        'updated_at': product.updated_at
    })

@app.route('/products', methods=['POST'])
def create_product():
    """
    Cria um novo produto
    """
    data = request.get_json()
    
    # Validação básica
    required_fields = ['id', 'name', 'price', 'category_id', 'supplier_id', 'sku']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Campo obrigatório ausente: {field}'}), 400
    
    product = Product(
        id=data['id'],
        name=data['name'],
        description=data.get('description'),
        price=data['price'],
        stock=data.get('stock', 0),
        category_id=data['category_id'],
        supplier_id=data['supplier_id'],
        features=data.get('features'),
        images=data.get('images'),
        status=data.get('status', 'active'),
        sku=data['sku']
    )
    
    db.session.add(product)
    
    # Registrar no histórico de preços se for um novo produto
    price_history = PriceHistory(
        product_id=product.id,
        previous_price=0,
        new_price=product.price,
        reason="Initial price"
    )
    db.session.add(price_history)
    
    try:
        db.session.commit()
        return jsonify({
            'id': product.id,
            'message': 'Produto criado com sucesso'
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/products/<product_id>', methods=['PUT'])
def update_product(product_id):
    """
    Atualiza um produto existente
    """
    product = Product.query.get_or_404(product_id)
    data = request.get_json()
    
    # Atualiza os campos fornecidos
    if 'name' in data:
        product.name = data['name']
    if 'description' in data:
        product.description = data['description']
    if 'price' in data and data['price'] != product.price:
        # Registrar mudança de preço no histórico
        price_history = PriceHistory(
            product_id=product.id,
            previous_price=product.price,
            new_price=data['price'],
            reason=data.get('price_change_reason')
        )
        db.session.add(price_history)
        product.price = data['price']
    if 'stock' in data:
        product.stock = data['stock']
    if 'category_id' in data:
        product.category_id = data['category_id']
    if 'supplier_id' in data:
        product.supplier_id = data['supplier_id']
    if 'features' in data:
        product.features = data['features']
    if 'images' in data:
        product.images = data['images']
    if 'status' in data:
        product.status = data['status']
    if 'sku' in data:
        product.sku = data['sku']
    
    try:
        db.session.commit()
        return jsonify({'message': 'Produto atualizado com sucesso'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/products/<product_id>', methods=['DELETE'])
def delete_product(product_id):
    """
    Remove um produto
    """
    product = Product.query.get_or_404(product_id)
    
    try:
        db.session.delete(product)
        db.session.commit()
        return jsonify({'message': 'Produto removido com sucesso'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/products/category/<category_id>', methods=['GET'])
def get_products_by_category(category_id):
    """
    Retorna produtos por categoria
    """
    products = Product.query.filter_by(category_id=category_id).all()
    return jsonify([{
        'id': product.id,
        'name': product.name,
        'price': product.price,
        'stock': product.stock,
        'status': product.status
    } for product in products])

@app.route('/products/supplier/<supplier_id>', methods=['GET'])
def get_products_by_supplier(supplier_id):
    """
    Retorna produtos por fornecedor
    """
    products = Product.query.filter_by(supplier_id=supplier_id).all()
    return jsonify([{
        'id': product.id,
        'name': product.name,
        'price': product.price,
        'stock': product.stock,
        'status': product.status
    } for product in products])

@app.route('/products/<product_id>/stock', methods=['PATCH'])
def update_stock(product_id):
    """
    Atualiza apenas o estoque de um produto
    """
    product = Product.query.get_or_404(product_id)
    data = request.get_json()
    
    if 'stock' not in data:
        return jsonify({'error': 'Campo stock é obrigatório'}), 400
    
    product.stock = data['stock']
    
    try:
        db.session.commit()
        return jsonify({
            'id': product.id,
            'stock': product.stock,
            'message': 'Estoque atualizado com sucesso'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/products/<product_id>/price', methods=['PATCH'])
def update_price(product_id):
    """
    Atualiza apenas o preço de um produto
    """
    product = Product.query.get_or_404(product_id)
    data = request.get_json()
    
    if 'price' not in data:
        return jsonify({'error': 'Campo price é obrigatório'}), 400
    
    if data['price'] != product.price:
        # Registrar mudança de preço no histórico
        price_history = PriceHistory(
            product_id=product.id,
            previous_price=product.price,
            new_price=data['price'],
            reason=data.get('reason')
        )
        db.session.add(price_history)
        product.price = data['price']
    
    try:
        db.session.commit()
        return jsonify({
            'id': product.id,
            'price': product.price,
            'message': 'Preço atualizado com sucesso'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/products/<product_id>/price_history', methods=['GET'])
def get_price_history(product_id):
    """
    Retorna o histórico de preços de um produto
    """
    Product.query.get_or_404(product_id)  # Verifica se o produto existe
    
    history = PriceHistory.query.filter_by(product_id=product_id).order_by(PriceHistory.change_date.desc()).all()
    return jsonify([{
        'previous_price': item.previous_price,
        'new_price': item.new_price,
        'change_date': item.change_date,
        'reason': item.reason
    } for item in history])

# Rota para verificar a saúde do serviço
@app.route('/health', methods=['GET'])
def health_check():
    """
    Endpoint para verificação de saúde do serviço
    """
    return jsonify({'status': 'ok', 'service': 'products'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)