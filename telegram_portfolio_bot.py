# telegram_portfolio_bot.py
# Yêu cầu: pip install python-telegram-bot vnstock pandas python-dotenv

import logging
import json
import os
import pandas as pd
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from vnstock import Vnstock

# === CONFIG ===
load_dotenv()
TOKEN = os.getenv("TOKEN")
DATA_FILE = 'user_data.json'

# === SETUP LOGGING ===
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# === HELPER FUNCTIONS ===
def load_data():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def get_price(symbol):
    try:
        stock = Vnstock().stock(symbol=symbol, source='VCI')
        df = stock.quote.history(start='2023-01-01', end=pd.Timestamp.today().strftime('%Y-%m-%d'), interval='1D')
        if df.empty:
            return None
        return df['close'].iloc[-1] * 1000
    except Exception as e:
        logging.warning(f"Lỗi khi lấy giá cho {symbol}: {e}")
        return None

# === START ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = (
        "👋 *Chào mừng đến với bot quản lý tài sản cá nhân!*\n\n"
        "Chọn chức năng:\n"
        "1. 🔍 Đánh giá xu thế cổ phiếu (đang phát triển)\n"
        "2. 📂 Quản lý danh mục đầu tư\n\n"
        "*Các lệnh quản lý danh mục:*\n"
        "/createp <tên>: Tạo danh mục\n"
        "/deletep <tên>: Xoá danh mục\n"
        "/showp: Xem danh mục hiện có\n"
        "/switchp <tên>: Chuyển danh mục hiện tại\n\n"
        "*Sau khi đã chọn danh mục, bạn có thể:*\n"
        "/add <mã> <số lượng> <giá mua>: Thêm cổ phiếu\n"
        "/remove <mã>: Xoá cổ phiếu\n"
        "/show: Hiển thị hiệu suất danh mục"
    )
    await update.message.reply_text(welcome, parse_mode='Markdown')

# === DANH MỤC ===
async def create_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    user_id = str(update.effective_user.id)
    args = context.args
    if len(args) != 1:
        await update.message.reply_text("Dùng: /createp TÊN")
        return
    name = args[0].lower()
    if user_id not in data:
        data[user_id] = {"__active__": name, name: {}}
    else:
        if name in data[user_id]:
            await update.message.reply_text("Tên danh mục đã tồn tại.")
            return
        data[user_id][name] = {}
        data[user_id]["__active__"] = name
    save_data(data)
    await update.message.reply_text(f"✅ Đã tạo danh mục '{name}' và đặt làm danh mục hiện tại.")

async def delete_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    user_id = str(update.effective_user.id)
    args = context.args
    if len(args) != 1:
        await update.message.reply_text("Dùng: /deletep TÊN")
        return
    name = args[0].lower()
    if user_id in data and name in data[user_id]:
        del data[user_id][name]
        if data[user_id].get("__active__") == name:
            data[user_id]["__active__"] = next((k for k in data[user_id].keys() if k != "__active__"), None)
        save_data(data)
        await update.message.reply_text(f"🗑️ Đã xoá danh mục '{name}'.")
    else:
        await update.message.reply_text(f"Danh mục '{name}' không tồn tại.")

async def switch_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    user_id = str(update.effective_user.id)
    args = context.args
    if len(args) != 1:
        await update.message.reply_text("Dùng: /switchp TÊN")
        return
    name = args[0].lower()
    if user_id not in data or name not in data[user_id]:
        await update.message.reply_text(f"Danh mục '{name}' không tồn tại.")
        return
    data[user_id]["__active__"] = name
    save_data(data)
    await update.message.reply_text(f"🔁 Đã chuyển sang danh mục '{name}'.")

async def list_portfolios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    user_id = str(update.effective_user.id)
    if user_id not in data:
        await update.message.reply_text("Bạn chưa có danh mục nào.")
        return
    active = data[user_id].get("__active__")
    portfolios = [k for k in data[user_id].keys() if k != "__active__"]
    if not portfolios:
        await update.message.reply_text("Bạn chưa có danh mục nào.")
        return
    response = "📂 Danh sách danh mục:\n"
    for name in portfolios:
        prefix = "👉 " if name == active else "- "
        response += f"{prefix}{name}\n"
    await update.message.reply_text(response)

# === CỔ PHIẾU TRONG DANH MỤC ===
async def add_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    user_id = str(update.effective_user.id)
    args = context.args
    if len(args) != 3:
        await update.message.reply_text("Cú pháp đúng: /add MÃ SỐ_LƯỢNG GIÁ_MUA")
        return
    if user_id not in data or "__active__" not in data[user_id]:
        await update.message.reply_text("Bạn chưa tạo danh mục nào. Dùng /createp TÊN")
        return
    symbol, qty, buy_price = args[0].upper(), int(args[1]), float(args[2]) * 1000
    portfolio = data[user_id][data[user_id]["__active__"]]
    portfolio[symbol] = {
        "quantity": qty,
        "buy_price": buy_price
    }
    save_data(data)
    await update.message.reply_text(f"✅ Đã thêm {qty} cổ phiếu {symbol} vào danh mục hiện tại.")

async def remove_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    user_id = str(update.effective_user.id)
    args = context.args
    if len(args) != 1:
        await update.message.reply_text("Cú pháp đúng: /remove MÃ")
        return
    if user_id not in data or "__active__" not in data[user_id]:
        await update.message.reply_text("Bạn chưa có danh mục để xoá cổ phiếu.")
        return
    symbol = args[0].upper()
    portfolio = data[user_id][data[user_id]["__active__"]]
    if symbol in portfolio:
        del portfolio[symbol]
        save_data(data)
        await update.message.reply_text(f"🗑️ Đã xoá {symbol} khỏi danh mục hiện tại.")
    else:
        await update.message.reply_text(f"{symbol} không có trong danh mục.")

async def show_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    user_id = str(update.effective_user.id)
    if user_id not in data or "__active__" not in data[user_id]:
        await update.message.reply_text("Bạn chưa tạo danh mục nào để hiển thị.")
        return
    portfolio = data[user_id][data[user_id]["__active__"]]
    if not portfolio:
        await update.message.reply_text("Danh mục hiện tại đang trống.")
        return
    response = f"📈 *Danh mục đầu tư:*\n"
    total_market_value = 0
    total_cost = 0
    for symbol, info in portfolio.items():
        qty = info['quantity']
        buy_price = info['buy_price']
        market_price = get_price(symbol)
        if market_price is None:
            response += f"- {symbol}: Không lấy được giá\n"
            continue
        cost_value = qty * buy_price
        market_value = qty * market_price
        pnl = market_value - cost_value
        pnl_percent = (pnl / cost_value) * 100 if cost_value > 0 else 0
        total_cost += cost_value
        total_market_value += market_value
        color = "🟢" if pnl >= 0 else "🔴"
        response += (
            f"{color} *{symbol}*\n"
            f"Số lượng: {qty}\n"
            f"Giá mua: {buy_price:,.0f}\n"
            f"Giá hiện tại: {market_price:,.0f}\n"
            f"Giá trị hiện tại: {market_value:,.0f}  VND\n"
            f"Lãi/Lỗ: {pnl:,.0f}  VND  ({pnl_percent:.2f}%)\n\n"
        )
    total_pnl = total_market_value - total_cost
    total_pnl_percent = (total_pnl / total_cost) * 100 if total_cost > 0 else 0
    total_color = "🟢" if total_pnl >= 0 else "🔴"
    response += f"{total_color} Tổng danh mục: {total_market_value:,.0f} VND\n{total_color} Tổng Lãi/Lỗ: {total_pnl:,.0f} VND ({total_pnl_percent:.2f}%)"
    await update.message.reply_text(response, parse_mode='Markdown')

# === MAIN FUNCTION ===
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("createp", create_portfolio))
    app.add_handler(CommandHandler("deletep", delete_portfolio))
    app.add_handler(CommandHandler("switchp", switch_portfolio))
    app.add_handler(CommandHandler("showp", list_portfolios))
    app.add_handler(CommandHandler("add", add_stock))
    app.add_handler(CommandHandler("remove", remove_stock))
    app.add_handler(CommandHandler("show", show_portfolio))

    print("Bot đang chạy...")
    app.run_polling()

if __name__ == '__main__':
    main()
