# app.py - Microserviço de Categorias
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import os

# Inicialização da aplicação Flask
app = Flask(__name__)

# Configuração do banco de dados
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///categories.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Modelo de dados - Categoria
class Category(db.Model):
    """
    Modelo para a tabela de categorias
    """
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(255), nullable=True)
    parent_id = db.Column(db.String(36), db.ForeignKey('category.id'), nullable=True)
    level = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), nullable=False, default='active')
    display_order = db.Column(db.Integer, nullable=False, default=0)
    attributes = db.Column(db.JSON, nullable=True)
    url_slug = db.Column(db.String(100), nullable=False, unique=True)
    
    # Relacionamento auto-referencial para subcategorias
    subcategories = db.relationship('Category', 
                                  backref=db.backref('parent', remote_side=[id]),
                                  lazy='dynamic')

# Criação das tabelas no banco de dados
with app.app_context():
    db.create_all()

# Rotas do microserviço

@app.route('/categories', methods=['GET'])
def get_all_categories():
    """
    Retorna todas as categorias
    """
    categories = Category.query.all()
    return jsonify([{
        'id': category.id,
        'name': category.name,
        'description': category.description,
        'parent_id': category.parent_id,
        'level': category.level,
        'status': category.status,
        'url_slug': category.url_slug
    } for category in categories])

@app.route('/categories/<category_id>', methods=['GET'])
def get_category(category_id):
    """
    Retorna uma categoria específica pelo ID
    """
    category = Category.query.get_or_404(category_id)
    return jsonify({
        'id': category.id,
        'name': category.name,
        'description': category.description,
        'image_url': category.image_url,
        'parent_id': category.parent_id,
        'level': category.level,
        'status': category.status,
        'display_order': category.display_order,
        'attributes': category.attributes,
        'url_slug': category.url_slug
    })

@app.route('/categories', methods=['POST'])
def create_category():
    """
    Cria uma nova categoria
    """
    data = request.get_json()
    
    # Validação básica
    required_fields = ['id', 'name', 'url_slug']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Campo obrigatório ausente: {field}'}), 400
    
    # Se tiver parent_id, verifica se a categoria pai existe e calcula o nível
    level = 1
    if data.get('parent_id'):
        parent = Category.query.get(data['parent_id'])
        if not parent:
            return jsonify({'error': 'Categoria pai não encontrada'}), 404
        level = parent.level + 1
    
    category = Category(
        id=data['id'],
        name=data['name'],
        description=data.get('description'),
        image_url=data.get('image_url'),
        parent_id=data.get('parent_id'),
        level=data.get('level', level),
        status=data.get('status', 'active'),
        display_order=data.get('display_order', 0),
        attributes=data.get('attributes'),
        url_slug=data['url_slug']
    )
    
    db.session.add(category)
    
    try:
        db.session.commit()
        return jsonify({
            'id': category.id,
            'message': 'Categoria criada com sucesso'
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/categories/<category_id>', methods=['PUT'])
def update_category(category_id):
    """
    Atualiza uma categoria existente
    """
    category = Category.query.get_or_404(category_id)
    data = request.get_json()
    
    # Atualiza os campos fornecidos
    if 'name' in data:
        category.name = data['name']
    if 'description' in data:
        category.description = data['description']
    if 'image_url' in data:
        category.image_url = data['image_url']
    if 'parent_id' in data:
        # Se mudar o parent_id, precisa recalcular o nível
        if data['parent_id'] != category.parent_id:
            if data['parent_id']:
                parent = Category.query.get(data['parent_id'])
                if not parent:
                    return jsonify({'error': 'Categoria pai não encontrada'}), 404
                category.level = parent.level + 1
            else:
                category.level = 1
        category.parent_id = data['parent_id']
    if 'status' in data:
        category.status = data['status']
    if 'display_order' in data:
        category.display_order = data['display_order']
    if 'attributes' in data:
        category.attributes = data['attributes']
    if 'url_slug' in data:
        category.url_slug = data['url_slug']
    
    try:
        db.session.commit()
        return jsonify({'message': 'Categoria atualizada com sucesso'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/categories/<category_id>', methods=['DELETE'])
def delete_category(category_id):
    """
    Remove uma categoria
    """
    category = Category.query.get_or_404(category_id)
    
    # Verifica se há subcategorias
    if category.subcategories.count() > 0:
        return jsonify({'error': 'Não é possível excluir categoria com subcategorias'}), 400
    
    try:
        db.session.delete(category)
        db.session.commit()
        return jsonify({'message': 'Categoria removida com sucesso'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/categories/hierarquia', methods=['GET'])
def get_hierarchy():
    """
    Retorna a hierarquia completa de categorias
    """
    # Busca apenas categorias de nível 1 (raiz)
    root_categories = Category.query.filter_by(level=1).all()
    
    def get_tree(category):
        """Função recursiva para construir a árvore de categorias"""
        children = category.subcategories.all()
        return {
            'id': category.id,
            'name': category.name,
            'url_slug': category.url_slug,
            'subcategories': [get_tree(child) for child in children]
        }
    
    result = [get_tree(category) for category in root_categories]
    return jsonify(result)

@app.route('/categories/atributos/<category_id>', methods=['GET'])
def get_category_attributes(category_id):
    """
    Retorna os atributos específicos de uma categoria
    """
    category = Category.query.get_or_404(category_id)
    
    attributes = category.attributes or {}
    
    # Se a categoria tiver pai, também inclui os atributos herdados
    if category.parent_id:
        parent = category.parent
        while parent:
            parent_attributes = parent.attributes or {}
            # Adiciona apenas atributos que não estão já definidos na categoria atual
            for key, value in parent_attributes.items():
                if key not in attributes:
                    attributes[key] = value
            
            parent = parent.parent if parent.parent_id else None
    
    return jsonify(attributes)

@app.route('/categories/slug/<url_slug>', methods=['GET'])
def get_category_by_slug(url_slug):
    """
    Retorna uma categoria pelo seu slug de URL
    """
    category = Category.query.filter_by(url_slug=url_slug).first_or_404()
    return jsonify({
        'id': category.id,
        'name': category.name,
        'description': category.description,
        'image_url': category.image_url,
        'parent_id': category.parent_id,
        'level': category.level,
        'status': category.status,
        'display_order': category.display_order,
        'attributes': category.attributes,
        'url_slug': category.url_slug
    })

# Rota para verificar a saúde do serviço
@app.route('/health', methods=['GET'])
def health_check():
    """
    Endpoint para verificação de saúde do serviço
    """
    return jsonify({'status': 'ok', 'service': 'categories'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)