import os
from flask import Flask
from flask_cors import CORS
from routes.views import views
from routes.api_produk import api_produk
from routes.api_qc import api_qc
from routes.api_misc import api_misc

app = Flask(__name__)
CORS(app)
app.secret_key = 'rahasia_spc_pabrik_123'
app.register_blueprint(views)
app.register_blueprint(api_produk)
app.register_blueprint(api_qc)
app.register_blueprint(api_misc)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)