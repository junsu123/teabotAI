import json
from pathlib import Path
import sys
import pytest
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import browser_listing as b
from telegram_listing_bot import parse_caption


@pytest.fixture
def instance(monkeypatch,tmp_path):
    monkeypatch.setattr(b,'DATA',tmp_path/'listing_data')
    monkeypatch.setattr(b,'DB',tmp_path/'listing_data'/'listings.sqlite3')
    monkeypatch.setattr(b,'FILES',tmp_path/'listing_data'/'images')
    monkeypatch.setattr(b,'PREVIEWS',tmp_path/'listing_data'/'previews')
    monkeypatch.setattr(b,'PROFILES',tmp_path/'listing_data'/'browser_profiles')
    monkeypatch.setattr(b,'RECORDINGS',tmp_path/'listing_data'/'recordings')
    monkeypatch.setattr(b,'PRODUCTS',tmp_path/'products.json')
    monkeypatch.setattr(b,'STEPS',tmp_path/'browser_steps.json')
    b.initialize()
    b.PRODUCTS.write_text(json.dumps({'TRA-001':{'title':'Trà thảo mộc thật','description':'Thông tin trung tính','price':39000,'stock':9}},ensure_ascii=False),encoding='utf-8')
    photo=tmp_path/'product.png'
    Image.new('RGB',(128,128),(240,220,210)).save(photo)
    return photo


def test_create_store_and_preview(instance):
    jid=b.create_job('TRA-001','shopee','new','123')
    assert b.get_job(jid)['sku']=='TRA-001'
    path=b.add_image(jid,instance)
    assert Path(path).exists()
    assert len(b.get_job(jid)['images'])==1
    b.add_image(jid,instance)
    assert len(b.get_job(jid)['images'])==1
    text=b.preview(jid).read_text(encoding='utf-8')
    assert 'Trà thảo mộc thật' in text
    b.update_state(jid,'approved',by='123')
    assert b.get_job(jid)['status']=='approved'
    # Database data survives new connections
    with b.connect() as conn:
        assert conn.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]==1


def test_duplicate_and_missing_prices(instance):
    a=b.create_job('TRA-001','tiktok','update','42')
    with pytest.raises(ValueError,match='Đang có nhiệm vụ'):
        b.create_job('TRA-001','tiktok','update','42')
    with pytest.raises(ValueError,match='Chưa có ảnh'):
        b.update_state(a,'approved',by='42')
    b.add_image(a,instance)
    b.update_state(a,'approved',by='42')
    with pytest.raises(ValueError):
        b.update_state(a,'posted',by='42')
    b.update_state(a,'editing')
    b.update_state(a,'needs_confirmation')
    b.update_state(a,'posted',by='42',product_url='https://example.org/p/1')
    assert b.get_job(a)['status']=='posted'


def test_invalid_file_and_url(instance,tmp_path):
    jid=b.create_job('TRA-001','shopee','new')
    wrong=tmp_path/'bad.jpg'
    wrong.write_text('just text',encoding='utf8')
    with pytest.raises(ValueError,match='ảnh hợp lệ'):
        b.add_image(jid,wrong)
    with pytest.raises(ValueError):
        b.validate_shop_url('shopee','http://banhang.shopee.vn/')
    with pytest.raises(ValueError):
        b.validate_shop_url('tiktok','https://evil.example/')
    assert b.validate_shop_url('tiktok','https://seller-vn.tiktok.com/')


def test_shop_automation_disabled(instance):
    jid=b.create_job('TRA-001','shopee','new')
    b.add_image(jid,instance)
    b.update_state(jid,'approved',by='123')
    class DummyPage:pass
    with pytest.raises(PermissionError):
        b.run_steps(DummyPage(),'shopee',b.get_job(jid),allowed=True)


def test_telegram_caption():
    assert parse_caption('SKU=TRA-001 SHOP=Shopee MODE=new')=={'sku':'TRA-001','shop':'shopee','mode':'new'}
    assert parse_caption('ADD=15')=={'add':15}
    with pytest.raises(ValueError):parse_caption('hello')
