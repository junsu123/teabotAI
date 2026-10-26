import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import shop_profiles as profiles
import browser_listing as listing
import telegram_listing_bot as telegram_bot

class ShopProfilesTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        base=Path(self.temp.name)
        self.stack=patch.multiple(profiles, DATA=base/'data', PROFILES=base/'data'/'profiles',
            SCHEMAS=base/'data'/'schemas', REGISTRY=base/'accounts.json')
        self.stack.start()
        self.dbpatch=patch.multiple(listing, DATA=base/'listing', DB=base/'listing'/'jobs.sqlite3',
            PROFILES=base/'listing'/'legacy', FILES=base/'listing'/'images',
            PREVIEWS=base/'listing'/'previews', RECORDINGS=base/'listing'/'recordings',
            PRODUCTS=base/'products.json', STEPS=base/'steps.json')
        self.dbpatch.start()
        profiles.init()
        listing.initialize()
        listing.PRODUCTS.write_text('{"SKU1":{"title":"Trà túi lọc","description":"Mô tả thật","price":39000,"stock":100}}', encoding='utf-8')

    def tearDown(self):
        self.dbpatch.stop()
        self.stack.stop()
        self.temp.cleanup()

    def test_account_separation_and_ceo_assignment(self):
        profiles.add_account('shop_01','shopee')
        profiles.add_account('shop_02','shopee')
        profiles.add_account('tiktok_01','tiktok')
        one=listing.create_job('SKU1','shopee','new',account_id='shop_01')
        two=listing.create_job('SKU1','shopee','new',account_id='shop_02')
        three=listing.create_job('SKU1','tiktok','new',account_id='tiktok_01')
        self.assertNotEqual(one,two)
        self.assertEqual(listing.get_job(three)['account_id'],'tiktok_01')
        with self.assertRaises(ValueError):
            listing.create_job('SKU1','tiktok','new',account_id='shop_01')
        with self.assertRaises(ValueError):
            listing.create_job('SKU1','shopee','new')
        with self.assertRaises(ValueError):
            listing.create_job('SKU1','shopee','new',account_id='shop_01')

    def test_proxy_credentials_not_serialized(self):
        profiles.add_account('shop_01','shopee', proxy_server='http://proxy.example:8080',proxy_env_prefix='TEST_PROXY')
        with patch.dict(os.environ,{'TEST_PROXY_USERNAME':'u','TEST_PROXY_PASSWORD':'supersecretxyz'}):
            self.assertEqual(profiles.resolve_proxy(profiles.get_account('shop_01'))['username'],'u')
        self.assertNotIn('supersecretxyz', profiles.REGISTRY.read_text(encoding='utf-8'))  # secret is not stored
        with self.assertRaises(ValueError):
            profiles.validate_proxy('http://user:pass@proxy.example:8080',None)
        with self.assertRaises(ValueError):
            profiles.validate_id('../secret')

    def test_validate_url(self):
        with self.assertRaises(ValueError):
            profiles.allowed_url('shopee','https://banhang.shopee.vn.evil.test')
        self.assertTrue(profiles.allowed_url('shopee','https://banhang.shopee.vn/'))

    def test_telegram_routes_multiple(self):
        fields=telegram_bot.parse_caption('SKU=SKU1 MODE=new ACCOUNTS=shop_01,tiktok_01')
        self.assertEqual(fields['accounts'],['shop_01','tiktok_01'])
        self.assertEqual(telegram_bot.parse_caption('ADD=123')['add'],123)
        with self.assertRaises(ValueError):
            telegram_bot.parse_caption('SKU=SKU1 MODE=new ACCOUNTS=shop_01,shop_01')

    def test_field_suggestions(self):
        self.assertEqual(profiles.suggest_field({'label':'Tên sản phẩm'})[0],'title')
        self.assertEqual(profiles.suggest_field({'name':'inventory'})[0],'stock')
        self.assertEqual(profiles.suggest_field({'tag':'input','type':'file'})[0],'images')

if __name__=='__main__':
    unittest.main()
