# app.py - Microserviço de Avaliações
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

# Inicialização da aplicação Flask
app = Flask(__name__)

# Configuração do banco de dados
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///reviews.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Modelo de dados - Avaliação
class Review(db.Model):
    """
    Modelo para a tabela de avaliações
    """
    id = db.Column(db.String(36), primary_key=True)
    product_id = db.Column(db.String(36), nullable=False)
    user_id = db.Column(db.String(36), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    comment = db.Column(db.Text, nullable=True)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    review_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    photos = db.Column(db.JSON, nullable=True)  # Array de URLs
    helpfulness = db.Column(db.JSON, nullable=False, default=lambda: {"likes": 0, "dislikes": 0})
    status = db.Column(db.String(20), nullable=False, default='pending')
    verified_purchase = db.Column(db.Boolean, nullable=False, default=False)
    attributes = db.Column(db.JSON, nullable=True)  # Avaliações específicas (durabilidade, etc)
    
    # Relacionamento com as respostas
    responses = db.relationship('ReviewResponse', backref='review', lazy='dynamic', cascade="all, delete-orphan")

# Modelo de dados - Resposta à Avaliação
class ReviewResponse(db.Model):
    """
    Modelo para a tabela de respostas às avaliações
    """
    id = db.Column(db.String(36), primary_key=True)
    review_id = db.Column(db.String(36), db.ForeignKey('review.id'), nullable=False)
    user_id = db.Column(db.String(36), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    response_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_seller = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(db.String(20), nullable=False, default='active')

# Modelo de dados - Resumo de Avaliações por Produto
class ReviewSummary(db.Model):
    """
    Modelo para a tabela de resumo de avaliações por produto
    """
    product_id = db.Column(db.String(36), primary_key=True)
    average_rating = db.Column(db.Float, nullable=False, default=0.0)
    total_reviews = db.Column(db.Integer, nullable=False, default=0)
    distribution = db.Column(db.JSON, nullable=False, default=lambda: {"5": 0, "4": 0, "3": 0, "2": 0, "1": 0})
    attribute_averages = db.Column(db.JSON, nullable=True)
    last_updated = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

# Criação das tabelas no banco de dados
with app.app_context():
    db.create_all()

# Funções auxiliares

def update_product_summary(product_id):
    """
    Atualiza o resumo das avaliações de um produto
    """
    # Busca todas as avaliações aprovadas do produto
    reviews = Review.query.filter_by(product_id=product_id, status='approved').all()
    
    if not reviews:
        # Se não houver avaliações aprovadas, cria/atualiza um resumo zerado
        summary = ReviewSummary.query.get(product_id)
        if not summary:
            summary = ReviewSummary(product_id=product_id)
            db.session.add(summary)
        summary.average_rating = 0
        summary.total_reviews = 0
        summary.distribution = {"5": 0, "4": 0, "3": 0, "2": 0, "1": 0}
        summary.attribute_averages = {}
        summary.last_updated = datetime.utcnow()
        return
    
    # Calcula a distribuição de avaliações
    distribution = {"5": 0, "4": 0, "3": 0, "2": 0, "1": 0}
    for review in reviews:
        distribution[str(review.rating)] += 1
    
    # Calcula a média de avaliações
    total_ratings = sum(int(key) * value for key, value in distribution.items())
    total_reviews = sum(distribution.values())
    average_rating = total_ratings / total_reviews if total_reviews > 0 else 0
    
    # Calcula médias de atributos específicos
    attributes = {}
    for review in reviews:
        if review.attributes:
            for attr, value in review.attributes.items():
                if attr not in attributes:
                    attributes[attr] = {"sum": 0, "count": 0}
                attributes[attr]["sum"] += value
                attributes[attr]["count"] += 1
    
    attribute_averages = {}
    for attr, data in attributes.items():
        attribute_averages[attr] = data["sum"] / data["count"] if data["count"] > 0 else 0
    
    # Atualiza ou cria o resumo
    summary = ReviewSummary.query.get(product_id)
    if not summary:
        summary = ReviewSummary(product_id=product_id)
        db.session.add(summary)
    
    summary.average_rating = round(average_rating, 2)
    summary.total_reviews = total_reviews
    summary.distribution = distribution
    summary.attribute_averages = attribute_averages
    summary.last_updated = datetime.utcnow()

# Rotas do microserviço

@app.route('/avaliacoes/produtos/<product_id>', methods=['GET'])
def get_product_reviews(product_id):
    """
    Retorna as avaliações de um produto
    """
    # Parâmetros opcionais
    status = request.args.get('status', 'approved')  # Por padrão, retorna apenas aprovadas
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    
    # Filtra as avaliações
    query = Review.query.filter_by(product_id=product_id)
    if status != 'all':
        query = query.filter_by(status=status)
    
    # Ordena por data (mais recente primeiro)
    query = query.order_by(Review.review_date.desc())
    
    # Paginação
    reviews = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'reviews': [{
            'id': review.id,
            'title': review.title,
            'comment': review.comment,
            'rating': review.rating,
            'review_date': review.review_date,
            'helpfulness': review.helpfulness,
            'user_id': review.user_id,
            'verified_purchase': review.verified_purchase,
            'photos': review.photos,
            'responses': [{
                'id': response.id,
                'comment': response.comment,
                'response_date': response.response_date,
                'is_seller': response.is_seller
            } for response in review.responses.filter_by(status='active').all()]
        } for review in reviews.items],
        'total': reviews.total,
        'pages': reviews.pages,
        'current_page': reviews.page
    })

@app.route('/avaliacoes/produtos/<product_id>/resumo', methods=['GET'])
def get_product_review_summary(product_id):
    """
    Retorna o resumo de avaliações de um produto
    """
    summary = ReviewSummary.query.get_or_404(product_id)
    
    return jsonify({
        'product_id': summary.product_id,
        'average_rating': summary.average_rating,
        'total_reviews': summary.total_reviews,
        'distribution': summary.distribution,
        'attribute_averages': summary.attribute_averages,
        'last_updated': summary.last_updated
    })

@app.route('/avaliacoes', methods=['POST'])
def create_review():
    """
    Cria uma nova avaliação
    """
    data = request.get_json()
    
    # Validação básica
    required_fields = ['id', 'product_id', 'user_id', 'title', 'rating']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Campo obrigatório ausente: {field}'}), 400
    
    # Validação de classificação
    if not 1 <= data['rating'] <= 5:
        return jsonify({'error': 'Classificação deve ser entre 1 e 5'}), 400
    
    review = Review(
        id=data['id'],
        product_id=data['product_id'],
        user_id=data['user_id'],
        title=data['title'],
        comment=data.get('comment'),
        rating=data['rating'],
        photos=data.get('photos'),
        verified_purchase=data.get('verified_purchase', False),
        attributes=data.get('attributes'),
        status='pending'  # Todas avaliações começam como pendentes
    )
    
    db.session.add(review)
    
    try:
        db.session.commit()
        return jsonify({
            'id': review.id,
            'message': 'Avaliação criada com sucesso',
            'status': review.status
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/avaliacoes/<review_id>/aprovar', methods=['PUT'])
def approve_review(review_id):
    """
    Aprova uma avaliação pendente
    """
    review = Review.query.get_or_404(review_id)
    
    if review.status != 'pending':
        return jsonify({'error': 'Apenas avaliações pendentes podem ser aprovadas'}), 400
    
    review.status = 'approved'
    
    try:
        db.session.commit()
        
        # Atualiza o resumo de avaliações do produto
        update_product_summary(review.product_id)
        db.session.commit()
        
        return jsonify({'message': 'Avaliação aprovada com sucesso'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/avaliacoes/<review_id>/rejeitar', methods=['PUT'])
def reject_review(review_id):
    """
    Rejeita uma avaliação pendente
    """
    review = Review.query.get_or_404(review_id)
    
    if review.status != 'pending':
        return jsonify({'error': 'Apenas avaliações pendentes podem ser rejeitadas'}), 400
    
    review.status = 'rejected'
    
    try:
        db.session.commit()
        return jsonify({'message': 'Avaliação rejeitada com sucesso'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/avaliacoes/<review_id>/respostas', methods=['POST'])
def create_review_response(review_id):
    """
    Adiciona uma resposta a uma avaliação
    """
    review = Review.query.get_or_404(review_id)
    data = request.get_json()
    
    # Validação básica
    required_fields = ['id', 'user_id', 'comment']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Campo obrigatório ausente: {field}'}), 400
    
    response = ReviewResponse(
        id=data['id'],
        review_id=review_id,
        user_id=data['user_id'],
        comment=data['comment'],
        is_seller=data.get('is_seller', False)
    )
    
    db.session.add(response)
    
    try:
        db.session.commit()
        return jsonify({
            'id': response.id,
            'message': 'Resposta adicionada com sucesso'
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/avaliacoes/<review_id>/utilidade', methods=['PATCH'])
def update_review_helpfulness(review_id):
    """
    Atualiza a utilidade de uma avaliação (likes/dislikes)
    """
    review = Review.query.get_or_404(review_id)
    data = request.get_json()
    
    if 'likes' in data:
        review.helpfulness['likes'] = data['likes']
    if 'dislikes' in data:
        review.helpfulness['dislikes'] = data['dislikes']
    
    try:
        db.session.commit()
        return jsonify({
            'helpfulness': review.helpfulness,
            'message': 'Utilidade atualizada com sucesso'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/avaliacoes/usuarios/<user_id>', methods=['GET'])
def get_user_reviews(user_id):
    """
    Retorna todas as avaliações de um usuário
    """
    reviews = Review.query.filter_by(user_id=user_id).all()
    
    return jsonify([{
        'id': review.id,
        'product_id': review.product_id,
        'title': review.title,
        'rating': review.rating,
        'review_date': review.review_date,
        'status': review.status
    } for review in reviews])

@app.route('/avaliacoes/pendentes', methods=['GET'])
def get_pending_reviews():
    """
    Retorna todas as avaliações pendentes de moderação
    """
    reviews = Review.query.filter_by(status='pending').all()
    
    return jsonify([{
        'id': review.id,
        'product_id': review.product_id,
        'user_id': review.user_id,
        'title': review.title,
        'comment': review.comment,
        'rating': review.rating,
        'review_date': review.review_date
    } for review in reviews])

# Rota para verificar a saúde do serviço
@app.route('/health', methods=['GET'])
def health_check():
    """
    Endpoint para verificação de saúde do serviço
    """
    return jsonify({'status': 'ok', 'service': 'reviews'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003)