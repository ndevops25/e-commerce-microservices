# app.py - Microserviço de Categorias (versão simplificada)
from flask import Flask, jsonify

# Inicialização da aplicação Flask
app = Flask(__name__)

# Dados de exemplo
sample_categories = [
    {
        "id": "cat-001",
        "name": "Eletrônicos",
        "description": "Produtos eletrônicos em geral",
        "image_url": "https://example.com/images/electronics.jpg",
        "parent_id": None,
        "level": 1,
        "status": "active",
        "url_slug": "eletronicos"
    },
    {
        "id": "cat-002",
        "name": "Smartphones",
        "description": "Telefones celulares inteligentes",
        "image_url": "https://example.com/images/smartphones.jpg",
        "parent_id": "cat-001",
        "level": 2,
        "status": "active",
        "url_slug": "smartphones"
    },
    {
        "id": "cat-003",
        "name": "Roupas",
        "description": "Vestuário em geral",
        "image_url": "https://example.com/images/clothing.jpg",
        "parent_id": None,
        "level": 1,
        "status": "active",
        "url_slug": "roupas"
    }
]

# Rotas do microserviço

@app.route('/categorias', methods=['GET'])
def get_all_categories():
    """
    Retorna todas as categorias
    """
    return jsonify(sample_categories)

@app.route('/health', methods=['GET'])
def health_check():
    """
    Endpoint para verificação de saúde do serviço
    """
    return jsonify({'status': 'ok', 'service': 'categorias'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6001)