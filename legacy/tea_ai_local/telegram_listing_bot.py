"""Telegram input/approval for local browser-assisted listings.

IMPORTANT: Uses only Telegram Bot API. It does not use any Shopee/TikTok API.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import tempfile

from browser_listing import create_job, add_image, get_job, update_state, preview, initialize


def parse_caption(caption: str) -> dict:
    # Send a photo with: SKU=XXX SHOP=shopee MODE=new, or ADD=123
    attrs=dict((k.upper(),v.strip()) for k,v in re.findall(r'(?i)\b(SKU|SHOP|MODE|ADD|ACCOUNT|ACCOUNTS)\s*[:=]\s*([\w.,-]+)',caption or ''))
    if 'ADD' in attrs:
        return {'add':int(attrs['ADD'])}
    if not attrs.get('SKU') or not attrs.get('MODE'):
        raise ValueError('Chú thích: SKU=TRA-001 MODE=new ACCOUNTS=shopee_01,tiktok_01 (hoặc ADD=123)')
    accounts=[a for a in (attrs.get('ACCOUNTS') or attrs.get('ACCOUNT') or '').split(',') if a]
    if len(set(accounts))!=len(accounts):raise ValueError('Trùng account_id trong ACCOUNTS')
    if not accounts and not attrs.get('SHOP'):
        raise ValueError('Cần ACCOUNT(S) hoặc SHOP')
    result={'sku':attrs['SKU'], 'shop':attrs.get('SHOP','').lower(),
            'mode':attrs['MODE'].lower()}
    if accounts:
        result['accounts']=accounts
    return result


def main():
    try:
        from telegram import Update
        from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
    except ImportError as e:
        raise SystemExit('Cài python-telegram-bot trước: pip install -r browser_requirements.txt') from e

    token=os.environ.get('TEA_TELEGRAM_TOKEN','')
    owners={int(x.strip()) for x in os.environ.get('TEA_TELEGRAM_ALLOWED_IDS','').split(',') if x.strip().isdigit()}
    if not token:
        raise SystemExit('Chưa có Telegram Bot Token. Vào Mars Studio → Cài đặt ChatGPT & Telegram.')
    # No configured owners: only /myid is available for safe onboarding.
    # All other commands use gate() and remain forbidden.
    initialize()

    async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if update.effective_message and user:
            await update.effective_message.reply_text(
                f'Telegram User ID của bạn là: {user.id}\\n'
                'Quay lại Mars Studio, điền ID này trong danh sách được phép, '
                'lưu và bật lại Bot để sử dụng các lệnh khác.')

    async def gate(update):
        user=update.effective_user
        if not user or user.id not in owners:
            if update.effective_message:
                await update.effective_message.reply_text('Bạn không được cấp quyền dùng bot này.')
            return False
        return True

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await gate(update): return
        await update.message.reply_text('TEA AI Browser Listing\nGửi ảnh kèm chú thích: SKU=TRA-001 MODE=new ACCOUNTS=shopee_01,tiktok_01\nThêm ảnh: ADD=ID\nDuyệt: /approve ID\nTrạng thái: /status ID')

    async def uploads(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await gate(update): return
        msg=update.effective_message
        if not msg: return
        doc=msg.document
        if doc and (not doc.mime_type or doc.mime_type.lower() not in ('image/png','image/jpeg','image/webp')):
            await msg.reply_text('Chỉ nhận ảnh PNG/JPG/WEBP.');return
        suffix=Path(doc.file_name or 'file.jpg').suffix.lower() if doc else '.jpg'
        if suffix not in ('.png','.jpg','.jpeg','.webp'):
            await msg.reply_text('File không phải PNG/JPG/WEBP');return
        payload=doc or (msg.photo[-1] if msg.photo else None)
        if payload is None: return
        if getattr(payload,'file_size',0) and payload.file_size > 15*1024*1024:
            await msg.reply_text('Ảnh vượt 15 MB');return
        try:
            instruction=parse_caption(msg.caption or '')
            from browser_listing import product,SHOP_URLS,MODES
            from shop_profiles import get_account
            if 'add' in instruction:
                ids=[instruction['add']]
                old=get_job(ids[0])
                if old['owner_id'] and old['owner_id']!=str(update.effective_user.id):
                    raise ValueError('Bạn không sở hữu nhiệm vụ này')
            else:
                if instruction['mode'] not in MODES:
                    raise ValueError('MODE không hợp lệ')
                product(instruction['sku'])
                ids=[]
                accounts=instruction.get('accounts',[])
                if accounts:
                    for account_id in accounts:
                        a=get_account(account_id)
                        if instruction['shop'] and instruction['shop']!=a['platform']:
                            raise ValueError(f'{account_id} không thuộc sàn đã chọn')
                elif instruction['shop'] not in SHOP_URLS:
                    raise ValueError('SHOP không hợp lệ')
            remote=await payload.get_file()
            with tempfile.TemporaryDirectory() as td:
                location=Path(td)/('image'+suffix)
                await remote.download_to_drive(custom_path=str(location))
                if 'add' not in instruction:
                    if instruction.get('accounts'):
                        ids=[create_job(instruction['sku'],get_account(a)['platform'],instruction['mode'],
                             str(update.effective_user.id),account_id=a) for a in instruction.get('accounts',[])]
                    else:
                        ids=[create_job(instruction['sku'],instruction['shop'],instruction['mode'],
                             str(update.effective_user.id))]
                for jid in ids:
                    add_image(jid,location)
            details=[]
            for jid in ids:
                j=get_job(jid)
                details.append(f'#{jid}: {j["account_id"] or j["shop"]} – {len(j["images"])} ảnh; /approve {jid}')
            await msg.reply_text('Đã nhận ảnh:\n'+'\n'.join(details)+'\nThêm ảnh từng job: ADD=ID')
        except Exception as e:
            await msg.reply_text(f'Không thể nhận ảnh: {type(e).__name__}: {e}')

    async def state_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await gate(update):return
        cmd=update.message.text.split()[0].split('@')[0].lower()
        try:
            jid=int(context.args[0]) if context.args else 0
            job=get_job(jid)
            if job['owner_id'] and job['owner_id']!=str(update.effective_user.id):
                raise ValueError('Bạn không sở hữu nhiệm vụ này')
            if cmd=='/approve':
                update_state(jid,'approved',by=str(update.effective_user.id))
                result=f'Đã duyệt job #{jid}. Lệnh trên PC: py -3 browser_listing.py work {jid}\nHoặc mở chế độ watch trên máy.'
            elif cmd=='/reject':
                update_state(jid,'rejected',by=str(update.effective_user.id))
                result=f'Đã từ chối #{jid}'
            else:
                result=(f'Job #{jid}: {job["status"]}\nSKU {job["sku"]}, shop {job["shop"]}, mode {job["mode"]}\n'
                        f'Account: {job.get("account_id") or "legacy"}\nẢnh: {len(job["images"])}\nGiá: {job["price"]}\nTồn: {job["stock"]}')
            await update.message.reply_text(result)
        except Exception as exc:
            await update.message.reply_text('Lỗi: '+str(exc))

    app=ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler('myid',myid))
    app.add_handler(CommandHandler('start',start))
    app.add_handler(CommandHandler('help',start))
    for cmd in ('approve','reject','status'):
        app.add_handler(CommandHandler(cmd,state_cmd))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, uploads))
    print('TEA AI Telegram Bot running. Shop APIs are not used.')
    app.run_polling(drop_pending_updates=False)


if __name__=='__main__':main()
