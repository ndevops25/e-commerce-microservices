# app.py - Microserviço de Fornecedores
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

# Inicialização da aplicação Flask
app = Flask(__name__)

# Configuração do banco de dados
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///suppliers.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Modelo de dados - Fornecedor
class Supplier(db.Model):
    """
    Modelo para a tabela de fornecedores
    """
    id = db.Column(db.String(36), primary_key=True)
    legal_name = db.Column(db.String(255), nullable=False)
    trading_name = db.Column(db.String(255), nullable=True)
    tax_id = db.Column(db.String(20), nullable=False, unique=True)  # CNPJ
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.JSON, nullable=False)  # Endereço completo
    status = db.Column(db.String(20), nullable=False, default='active')
    registration_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    update_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    representative = db.Column(db.String(100), nullable=True)
    payment_terms = db.Column(db.String(100), nullable=True)
    
    # Relacionamentos
    contacts = db.relationship('SupplierContact', backref='supplier', lazy='dynamic', cascade="all, delete-orphan")
    deliveries = db.relationship('SupplierDelivery', backref='supplier', lazy='dynamic', cascade="all, delete-orphan")

# Modelo de dados - Contatos do Fornecedor
class SupplierContact(db.Model):
    """
    Modelo para a tabela de contatos de fornecedores
    """
    id = db.Column(db.String(36), primary_key=True)
    supplier_id = db.Column(db.String(36), db.ForeignKey('supplier.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    department = db.Column(db.String(50), nullable=True)
    is_primary = db.Column(db.Boolean, nullable=False, default=False)

# Modelo de dados - Entregas do Fornecedor
class SupplierDelivery(db.Model):
    """
    Modelo para a tabela de entregas de fornecedores
    """
    id = db.Column(db.String(36), primary_key=True)
    supplier_id = db.Column(db.String(36), db.ForeignKey('supplier.id'), nullable=False)
    delivery_date = db.Column(db.DateTime, nullable=False)
    products = db.Column(db.JSON, nullable=False)  # Lista de produtos entregues
    status = db.Column(db.String(50), nullable=False, default='pending')
    invoice_number = db.Column(db.String(50), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

# Criação das tabelas no banco de dados
with app.app_context():
    db.create_all()

# Rotas do microserviço

@app.route('/suppliers', methods=['GET'])
def get_all_suppliers():
    """
    Retorna todos os fornecedores
    """
    suppliers = Supplier.query.all()
    return jsonify([{
        'id': supplier.id,
        'legal_name': supplier.legal_name,
        'trading_name': supplier.trading_name,
        'tax_id': supplier.tax_id,
        'email': supplier.email,
        'status': supplier.status
    } for supplier in suppliers])

@app.route('/suppliers/<supplier_id>', methods=['GET'])
def get_supplier(supplier_id):
    """
    Retorna um fornecedor específico pelo ID
    """
    supplier = Supplier.query.get_or_404(supplier_id)
    return jsonify({
        'id': supplier.id,
        'legal_name': supplier.legal_name,
        'trading_name': supplier.trading_name,
        'tax_id': supplier.tax_id,
        'email': supplier.email,
        'phone': supplier.phone,
        'address': supplier.address,
        'status': supplier.status,
        'registration_date': supplier.registration_date,
        'update_date': supplier.update_date,
        'representative': supplier.representative,
        'payment_terms': supplier.payment_terms
    })

@app.route('/suppliers', methods=['POST'])
def create_supplier():
    """
    Cria um novo fornecedor
    """
    data = request.get_json()
    
    # Validação básica
    required_fields = ['id', 'legal_name', 'tax_id', 'email', 'phone', 'address']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Campo obrigatório ausente: {field}'}), 400
    
    supplier = Supplier(
        id=data['id'],
        legal_name=data['legal_name'],
        trading_name=data.get('trading_name'),
        tax_id=data['tax_id'],
        email=data['email'],
        phone=data['phone'],
        address=data['address'],
        status=data.get('status', 'active'),
        representative=data.get('representative'),
        payment_terms=data.get('payment_terms')
    )
    
    db.session.add(supplier)
    
    try:
        db.session.commit()
        return jsonify({
            'id': supplier.id,
            'message': 'Fornecedor criado com sucesso'
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/suppliers/<supplier_id>', methods=['PUT'])
def update_supplier(supplier_id):
    """
    Atualiza um fornecedor existente
    """
    supplier = Supplier.query.get_or_404(supplier_id)
    data = request.get_json()
    
    # Atualiza os campos fornecidos
    if 'legal_name' in data:
        supplier.legal_name = data['legal_name']
    if 'trading_name' in data:
        supplier.trading_name = data['trading_name']
    if 'tax_id' in data:
        supplier.tax_id = data['tax_id']
    if 'email' in data:
        supplier.email = data['email']
    if 'phone' in data:
        supplier.phone = data['phone']
    if 'address' in data:
        supplier.address = data['address']
    if 'status' in data:
        supplier.status = data['status']
    if 'representative' in data:
        supplier.representative = data['representative']
    if 'payment_terms' in data:
        supplier.payment_terms = data['payment_terms']
    
    try:
        db.session.commit()
        return jsonify({'message': 'Fornecedor atualizado com sucesso'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/suppliers/<supplier_id>', methods=['DELETE'])
def delete_supplier(supplier_id):
    """
    Remove um fornecedor
    """
    supplier = Supplier.query.get_or_404(supplier_id)
    
    try:
        db.session.delete(supplier)
        db.session.commit()
        return jsonify({'message': 'Fornecedor removido com sucesso'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/suppliers/ativos', methods=['GET'])
def get_active_suppliers():
    """
    Retorna todos os fornecedores ativos
    """
    suppliers = Supplier.query.filter_by(status='active').all()
    return jsonify([{
        'id': supplier.id,
        'legal_name': supplier.legal_name,
        'trading_name': supplier.trading_name,
        'email': supplier.email,
        'phone': supplier.phone
    } for supplier in suppliers])

@app.route('/suppliers/<supplier_id>/contacts', methods=['GET'])
def get_supplier_contacts(supplier_id):
    """
    Retorna todos os contatos de um fornecedor
    """
    Supplier.query.get_or_404(supplier_id)  # Verifica se o fornecedor existe
    
    contacts = SupplierContact.query.filter_by(supplier_id=supplier_id).all()
    return jsonify([{
        'id': contact.id,
        'name': contact.name,
        'position': contact.position,
        'email': contact.email,
        'phone': contact.phone,
        'department': contact.department,
        'is_primary': contact.is_primary
    } for contact in contacts])

@app.route('/suppliers/<supplier_id>/contacts', methods=['POST'])
def create_supplier_contact(supplier_id):
    """
    Cria um novo contato para um fornecedor
    """
    Supplier.query.get_or_404(supplier_id)  # Verifica se o fornecedor existe
    data = request.get_json()
    
    # Validação básica
    required_fields = ['id', 'name', 'email', 'phone']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Campo obrigatório ausente: {field}'}), 400
    
    contact = SupplierContact(
        id=data['id'],
        supplier_id=supplier_id,
        name=data['name'],
        position=data.get('position'),
        email=data['email'],
        phone=data['phone'],
        department=data.get('department'),
        is_primary=data.get('is_primary', False)
    )
    
    # Se este contato for marcado como primário, desmarque qualquer outro
    if contact.is_primary:
        existing_primary = SupplierContact.query.filter_by(
            supplier_id=supplier_id, is_primary=True
        ).first()
        if existing_primary:
            existing_primary.is_primary = False
    
    db.session.add(contact)
    
    try:
        db.session.commit()
        return jsonify({
            'id': contact.id,
            'message': 'Contato criado com sucesso'
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/suppliers/<supplier_id>/contacts/<contact_id>', methods=['PUT'])
def update_supplier_contact(supplier_id, contact_id):
    """
    Atualiza um contato existente de um fornecedor
    """
    Supplier.query.get_or_404(supplier_id)  # Verifica se o fornecedor existe
    contact = SupplierContact.query.get_or_404(contact_id)
    
    # Verifica se o contato pertence ao fornecedor
    if contact.supplier_id != supplier_id:
        return jsonify({'error': 'Contato não pertence a este fornecedor'}), 404
    
    data = request.get_json()
    
    # Atualiza os campos fornecidos
    if 'name' in data:
        contact.name = data['name']
    if 'position' in data:
        contact.position = data['position']
    if 'email' in data:
        contact.email = data['email']
    if 'phone' in data:
        contact.phone = data['phone']
    if 'department' in data:
        contact.department = data['department']
    if 'is_primary' in data and data['is_primary'] != contact.is_primary:
        # Se estiver definindo este contato como primário
        if data['is_primary']:
            existing_primary = SupplierContact.query.filter_by(
                supplier_id=supplier_id, is_primary=True
            ).first()
            if existing_primary:
                existing_primary.is_primary = False
        contact.is_primary = data['is_primary']
    
    try:
        db.session.commit()
        return jsonify({'message': 'Contato atualizado com sucesso'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/suppliers/<supplier_id>/deliveries', methods=['GET'])
def get_supplier_deliveries(supplier_id):
    """
    Retorna todas as entregas de um fornecedor
    """
    Supplier.query.get_or_404(supplier_id)  # Verifica se o fornecedor existe
    
    deliveries = SupplierDelivery.query.filter_by(supplier_id=supplier_id).all()
    return jsonify([{
        'id': delivery.id,
        'delivery_date': delivery.delivery_date,
        'status': delivery.status,
        'invoice_number': delivery.invoice_number,
        'products': delivery.products
    } for delivery in deliveries])

@app.route('/suppliers/<supplier_id>/deliveries', methods=['POST'])
def create_supplier_delivery(supplier_id):
    """
    Cria uma nova entrega para um fornecedor
    """
    Supplier.query.get_or_404(supplier_id)  # Verifica se o fornecedor existe
    data = request.get_json()
    
    # Validação básica
    required_fields = ['id', 'delivery_date', 'products']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Campo obrigatório ausente: {field}'}), 400
    
    delivery = SupplierDelivery(
        id=data['id'],
        supplier_id=supplier_id,
        delivery_date=datetime.fromisoformat(data['delivery_date']),
        products=data['products'],
        status=data.get('status', 'pending'),
        invoice_number=data.get('invoice_number'),
        notes=data.get('notes')
    )
    
    db.session.add(delivery)
    
    try:
        db.session.commit()
        return jsonify({
            'id': delivery.id,
            'message': 'Entrega criada com sucesso'
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/suppliers/<supplier_id>/deliveries/<delivery_id>', methods=['PUT'])
def update_supplier_delivery(supplier_id, delivery_id):
    """
    Atualiza uma entrega existente de um fornecedor
    """
    Supplier.query.get_or_404(supplier_id)  # Verifica se o fornecedor existe
    delivery = SupplierDelivery.query.get_or_404(delivery_id)
    
    # Verifica se a entrega pertence ao fornecedor
    if delivery.supplier_id != supplier_id:
        return jsonify({'error': 'Entrega não pertence a este fornecedor'}), 404
    
    data = request.get_json()
    
    # Atualiza os campos fornecidos
    if 'delivery_date' in data:
        delivery.delivery_date = datetime.fromisoformat(data['delivery_date'])
    if 'products' in data:
        delivery.products = data['products']
    if 'status' in data:
        delivery.status = data['status']
    if 'invoice_number' in data:
        delivery.invoice_number = data['invoice_number']
    if 'notes' in data:
        delivery.notes = data['notes']
    
    try:
        db.session.commit()
        return jsonify({'message': 'Entrega atualizada com sucesso'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/suppliers/<supplier_id>/pedidos', methods=['POST'])
def create_supplier_order(supplier_id):
    """
    Cria um novo pedido para um fornecedor
    """
    Supplier.query.get_or_404(supplier_id)  # Verifica se o fornecedor existe
    data = request.get_json()
    
    # Esta rota simula a criação de um pedido
    # Em um sistema real, teria uma tabela SupplierOrder
    
    # Validação básica
    required_fields = ['products']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Campo obrigatório ausente: {field}'}), 400
    
    # Simulando criação de pedido com resposta de sucesso
    # Normalmente, salvaríamos o pedido no banco e retornaríamos seu ID
    return jsonify({
        'order_id': 'pedido-' + supplier_id[:8],
        'supplier_id': supplier_id,
        'products': data['products'],
        'status': 'pending',
        'message': 'Pedido criado com sucesso'
    }), 201

# Rota para verificar a saúde do serviço
@app.route('/health', methods=['GET'])
def health_check():
    """
    Endpoint para verificação de saúde do serviço
    """
    return jsonify({'status': 'ok', 'service': 'suppliers'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)