from flask import Flask, render_template, make_response

app = Flask(__name__)

# প্রোডাক্ট ডেটা
products = {
    'iphone-18-pro-max': {
        'name': 'iPhone 18 Pro Max',
        'price': '175,000 BDT',
        'image_url': 'https://images.unsplash.com/photo-1592750475338-74b7b21085ab?q=80&w=800&auto=format&fit=crop',
        'description': 'The upcoming iPhone 18 Pro Max features Apple\'s next-generation A19 Bionic chip, under-display Face ID, and advanced camera features. Pre-order at Nafiz Store.'
    },
    'iphone15pro': {
        'name': 'iPhone 15 Pro',
        'price': '135,000 BDT',
        'image_url': 'https://images.unsplash.com/photo-1592750475338-74b7b21085ab?q=80&w=800&auto=format&fit=crop',
        'description': 'Official iPhone 15 Pro with Titanium design and A17 Pro chip.'
    }
}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/phone-detail/<name>')
def phone_detail(name):
    phone = products.get(name)
    if not phone:
        phone = {
            'name': name.replace('-', ' ').title(),
            'price': '175,000 BDT',
            'image_url': 'https://images.unsplash.com/photo-1592750475338-74b7b21085ab?q=80&w=800&auto=format&fit=crop',
            'description': f'Buy {name.replace("-", " ").title()} at best price in BD.'
        }
    return render_template('product_phone.html', phone=phone, slug=name)

# SEO Routes (Robots & Sitemap)
@app.route('/robots.txt')
def robots():
    response = make_response("""User-agent: *
Allow: /
Sitemap: https://nafiz-ahmed12s.onrender.com/sitemap.xml
""")
    response.headers['Content-Type'] = 'text/plain'
    return response

@app.route('/sitemap.xml')
def sitemap():
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml += '  <url><loc>https://nafiz-ahmed12s.onrender.com/</loc><priority>1.0</priority></url>\n'
    for slug in products.keys():
        xml += f'  <url><loc>https://nafiz-ahmed12s.onrender.com/phone-detail/{slug}</loc><priority>0.9</priority></url>\n'
    xml += '</urlset>'
    
    response = make_response(xml)
    response.headers['Content-Type'] = 'application/xml'
    return response

if __name__ == '__main__':
    app.run(debug=True)
