import json
import os
from datetime import datetime
from flask import Flask, render_template, abort, request, make_response

app = Flask(__name__)

# JSON ফাইল থেকে প্রোডাক্ট লোড করার হেল্পার ফাংশন
def load_phones():
    json_path = os.path.join(app.root_path, 'products.json')
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

@app.route('/')
def home():
    phones = load_phones()
    return render_template('index.html', phones=phones)

# ডায়নামিক প্রোডাক্ট পেজ রুট
@app.route('/phone/<slug>')
def product_page(slug):
    phones = load_phones()
    phone = phones.get(slug)
    
    if not phone:
        abort(404)
        
    current_year = datetime.now().year
    return render_template(
        'product_phone.html', 
        phone=phone, 
        slug=slug, 
        current_year=current_year
    )

# ডায়নামিক সাইটম্যাপ (SEO Optimization)
@app.route('/sitemap.xml', methods=['GET'])
def sitemap():
    phones = load_phones()
    host_url = request.host_url.rstrip('/')
    
    urls = [
        {
            'loc': f"{host_url}/",
            'lastmod': datetime.now().strftime('%Y-%m-%d'),
            'changefreq': 'daily',
            'priority': '1.0'
        }
    ]
    
    for slug in phones.keys():
        urls.append({
            'loc': f"{host_url}/phone/{slug}",
            'lastmod': datetime.now().strftime('%Y-%m-%d'),
            'changefreq': 'weekly',
            'priority': '0.8'
        })

    xml_sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_sitemap += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for url in urls:
        xml_sitemap += '  <url>\n'
        xml_sitemap += f'    <loc>{url["loc"]}</loc>\n'
        xml_sitemap += f'    <lastmod>{url["lastmod"]}</lastmod>\n'
        xml_sitemap += f'    <changefreq>{url["changefreq"]}</changefreq>\n'
        xml_sitemap += f'    <priority>{url["priority"]}</priority>\n'
        xml_sitemap += '  </url>\n'
    xml_sitemap += '</urlset>'

    response = make_response(xml_sitemap)
    response.headers["Content-Type"] = "application/xml"
    return response

if __name__ == '__main__':
    app.run(debug=True)
