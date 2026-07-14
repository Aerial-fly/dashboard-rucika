import urllib.request
import urllib.parse
import json

data = urllib.parse.urlencode({
    'id': 1, 
    'nama_produk': 'Produk A', 
    'parameter_dinamis': '[{"name": "Suhu", "chartType": "Line"}]'
}).encode('utf-8')

req = urllib.request.Request('http://127.0.0.1:5000/api/edit-produk', data=data)
urllib.request.urlopen(req)

res = urllib.request.urlopen('http://127.0.0.1:5000/api/get-produk/1').read()
print(res)
