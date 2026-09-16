"""
Update existing mobiles in SQLite with photos and hardware specs
"""
from app import create_app
from models import db, Mobile

app = create_app()

specs_map = {
    'iPhone 15 Pro Max': {
        'image_url': 'https://images.unsplash.com/photo-1695048133142-1a20484d2569?w=500&auto=format&fit=crop&q=80',
        'display': '6.7" Super Retina XDR OLED, 120Hz ProMotion',
        'processor': 'Apple A17 Pro (3nm)',
        'camera': '48MP Main + 12MP Ultra-wide + 12MP 5x Telephoto',
        'battery': '4422 mAh, 25W Fast Charge, MagSafe'
    },
    'iPhone 14': {
        'image_url': 'https://images.unsplash.com/photo-1678685888221-cda773a3dcdb?w=500&auto=format&fit=crop&q=80',
        'display': '6.1" Super Retina XDR OLED, HDR10',
        'processor': 'Apple A15 Bionic (5nm)',
        'camera': '12MP Dual Pixel OIS + 12MP Ultra-wide',
        'battery': '3279 mAh, 20W Fast Charge'
    },
    'Galaxy S24 Ultra': {
        'image_url': 'https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?w=500&auto=format&fit=crop&q=80',
        'display': '6.8" Dynamic LTPO AMOLED 2X, 120Hz, 2600 nits',
        'processor': 'Snapdragon 8 Gen 3 for Galaxy (4nm)',
        'camera': '200MP OIS + 50MP 5x Periscope + 10MP 3x + 12MP Ultra-wide',
        'battery': '5000 mAh, 45W Wired, 15W Wireless'
    },
    'Galaxy A55': {
        'image_url': 'https://images.unsplash.com/photo-1580910051074-3eb694886505?w=500&auto=format&fit=crop&q=80',
        'display': '6.6" Super AMOLED 120Hz Gorilla Glass Victus+',
        'processor': 'Samsung Exynos 1480 (4nm)',
        'camera': '50MP OIS Main + 12MP Ultra-wide + 5MP Macro',
        'battery': '5000 mAh, 25W Fast Charging'
    },
    'OnePlus 12': {
        'image_url': 'https://images.unsplash.com/photo-1565849904461-04a58ad377e0?w=500&auto=format&fit=crop&q=80',
        'display': '6.82" 2K 120Hz ProXDR LTPO AMOLED, 4500 nits',
        'processor': 'Snapdragon 8 Gen 3 (4nm)',
        'camera': '50MP Sony LYT-808 + 64MP 3x Periscope + 48MP Ultra-wide',
        'battery': '5400 mAh, 100W SUPERVOOC, 50W AIRVOOC'
    },
    'Nord CE 4': {
        'image_url': 'https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=500&auto=format&fit=crop&q=80',
        'display': '6.7" Fluid AMOLED, 120Hz, HDR10+',
        'processor': 'Snapdragon 7 Gen 3 (4nm)',
        'camera': '50MP Sony LYT-600 OIS + 8MP Ultra-wide',
        'battery': '5500 mAh, 100W SuperVOOC Fast Charge'
    },
    'Redmi Note 13': {
        'image_url': 'https://images.unsplash.com/photo-1546868871-7041f2a55e12?w=500&auto=format&fit=crop&q=80',
        'display': '6.67" 1.5K Curved AMOLED, 120Hz, Dolby Vision',
        'processor': 'MediaTek Dimensity 7200 Ultra (4nm)',
        'camera': '200MP Samsung ISOCELL HP3 OIS + 8MP + 2MP',
        'battery': '5000 mAh, 120W HyperCharge'
    },
    '12 Pro+': {
        'image_url': 'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=500&auto=format&fit=crop&q=80',
        'display': '6.7" 120Hz Curved Vision AMOLED',
        'processor': 'Snapdragon 7s Gen 2 (4nm)',
        'camera': '64MP Periscope OIS + 50MP Sony IMX890 + 8MP',
        'battery': '5000 mAh, 67W SUPERVOOC Charge'
    },
    'V30 Pro': {
        'image_url': 'https://images.unsplash.com/photo-1574944985070-8f3ebc6b79d2?w=500&auto=format&fit=crop&q=80',
        'display': '6.78" 1.5K 3D Curved AMOLED 120Hz, 2800 nits',
        'processor': 'MediaTek Dimensity 8200 (4nm)',
        'camera': '50MP ZEISS Main + 50MP ZEISS Telephoto + 50MP Ultra-wide',
        'battery': '5000 mAh, 80W FlashCharge'
    },
    'Edge 50 Pro': {
        'image_url': 'https://images.unsplash.com/photo-1585060544812-6b45742d762f?w=500&auto=format&fit=crop&q=80',
        'display': '6.7" 1.5K True Color pOLED 144Hz, Pantone Validated',
        'processor': 'Snapdragon 7 Gen 3 (4nm)',
        'camera': '50MP AI OIS + 10MP 3x Telephoto + 13MP Macro/Ultra-wide',
        'battery': '4500 mAh, 125W TurboPower, 50W Wireless'
    }
}

with app.app_context():
    # Execute ALTER table for SQLite if columns don't exist yet
    for col_def in [
        ("image_url", "VARCHAR(350)"),
        ("display", "VARCHAR(120)"),
        ("processor", "VARCHAR(120)"),
        ("camera", "VARCHAR(120)"),
        ("battery", "VARCHAR(80)")
    ]:
        try:
            db.session.execute(db.text(f"ALTER TABLE mobiles ADD COLUMN {col_def[0]} {col_def[1]}"))
            db.session.commit()
        except Exception:
            db.session.rollback()

    mobiles = Mobile.query.all()
    count = 0
    for m in mobiles:
        for key, s in specs_map.items():
            if key.lower() in m.model.lower():
                m.image_url = s['image_url']
                m.display = s['display']
                m.processor = s['processor']
                m.camera = s['camera']
                m.battery = s['battery']
                count += 1
                break
    db.session.commit()
    print(f"[SUCCESS] Updated {count} mobiles with high-res photos and hardware specifications!")
