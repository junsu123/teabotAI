import sys
from pathlib import Path
import tempfile,unittest
from unittest.mock import patch
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE))
import proxy_store as px
import shop_profiles
import browser_trainer

class GuiV2Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  root=Path(self.tmp.name)
  self.p1=patch.multiple(shop_profiles,DATA=root/'legacy',PROFILES=root/'legacy'/'accounts',SCHEMAS=root/'legacy'/'schema',REGISTRY=root/'shop_accounts.json')
  self.p2=patch.object(px,'DB',root/'proxies.sqlite3')
  self.p1.start();self.p2.start()
  shop_profiles.init();px.init()
 def tearDown(self):
  self.p2.stop();self.p1.stop();self.tmp.cleanup()
 def test_proxy_crud_account_binding_and_secret_free(self):
  px.save_proxy('proxy_01','Máy chủ A','http','192.0.2.3',8080)
  shop_profiles.add_account('shopee_01','shopee')
  px.assign_proxy('shopee_01','proxy_01')
  self.assertEqual(shop_profiles.get_account('shopee_01')['proxy_id'],'proxy_01')
  self.assertEqual(shop_profiles.get_account('shopee_01')['proxy']['server'],'http://192.0.2.3:8080')
  px.save_proxy('proxy_01','Máy chủ B','socks5','192.0.2.5',1080,edit=True)
  self.assertEqual(shop_profiles.get_account('shopee_01')['proxy']['server'],'socks5://192.0.2.5:1080')
  with self.assertRaises(ValueError):px.delete_proxy('proxy_01')
  px.assign_proxy('shopee_01','')
  px.delete_proxy('proxy_01')
  self.assertEqual(px.all_proxies(),[])
 def test_creds_must_use_keyring(self):
  with patch.object(px,'_keyring',side_effect=RuntimeError('keyring unavailable')):
   with self.assertRaises(RuntimeError):
    px.save_proxy('proxy_02','Tên proxy','http','127.0.0.1',8888,'user','password123')
  self.assertEqual(px.all_proxies(),[])
 def test_locked_profile_rejects_switch(self):
  px.save_proxy('proxy_01','A','http','192.0.2.3',8080)
  shop_profiles.add_account('shopee_01','shopee')
  (shop_profiles.PROFILES/'shopee_01'/'.tea_ai_in_use').touch()
  with self.assertRaises(ValueError):px.assign_proxy('shopee_01','proxy_01')
 def test_trainer_never_collects_field_values(self):
  src=browser_trainer.RECORDER
  self.assertIn('ev.isTrusted',src)
  self.assertIn('password',src)
  self.assertNotIn('element.value',src)
  self.assertNotIn('document.cookie',src)
  self.assertNotIn('localStorage',src)

if __name__=='__main__': unittest.main()
