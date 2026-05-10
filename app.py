"""
日本株テーマトラッカー - Renderデプロイ版
プライム市場上位500銘柄をカバー
30分ごとに自動更新
"""

import os
import time
import json
import logging
import threading
import requests
import io
from datetime import datetime
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__, static_folder="static")
CORS(app)

# ===== プライム市場上位500銘柄（時価総額順） =====
PRIME_500 = [
    # メガキャップ
    "7203.T","8306.T","6758.T","9432.T","8316.T","4502.T","8035.T",
    "9984.T","6861.T","7974.T","8031.T","8058.T","8001.T","9433.T",
    "6902.T","4063.T","8802.T","8801.T","7267.T","6954.T","4519.T",
    "9022.T","6501.T","8411.T","5108.T","8766.T","9020.T","6367.T",
    "4568.T","8309.T","7751.T","6857.T","4523.T","7741.T","9021.T",
    "6098.T","8604.T","3382.T","2914.T","4543.T","8630.T","8750.T",
    "9005.T","9007.T","4507.T","7011.T","8253.T","5401.T","8725.T",
    "6902.T","4578.T","2802.T","4661.T","9433.T","3407.T","6723.T",
    # AI・半導体
    "8035.T","6857.T","6920.T","6723.T","4063.T","285A.T","6758.T",
    "6981.T","6645.T","4186.T","6701.T","6702.T","6976.T","3436.T",
    "6146.T","6963.T","6967.T","6506.T","6861.T","6988.T","4062.T",
    "6440.T","6754.T","4004.T","6503.T",
    # 自動車・輸送機器
    "7203.T","7267.T","7269.T","7270.T","7211.T","7261.T","7201.T",
    "7272.T","7282.T","7248.T","7259.T","7276.T","7278.T","5802.T",
    "5105.T","6594.T","6472.T","6471.T","6273.T","5108.T","7012.T",
    # 金融・保険
    "8306.T","8316.T","8411.T","8309.T","8308.T","8304.T","8331.T",
    "8332.T","8355.T","8253.T","8591.T","8601.T","8604.T","8630.T",
    "8750.T","8725.T","8766.T","8282.T","7182.T","8473.T","8698.T",
    "8697.T","8572.T","8570.T","8585.T","8252.T","8354.T","8356.T",
    # 商社・資源
    "8058.T","8031.T","8001.T","8002.T","8053.T","1605.T","5713.T",
    "5714.T","8015.T","8025.T","8020.T","8075.T","5401.T","5411.T",
    "5406.T","5703.T","5711.T","3407.T","4005.T","4021.T","4041.T",
    # 医薬品・ヘルスケア
    "4502.T","4519.T","4568.T","4523.T","4507.T","4578.T","4543.T",
    "4528.T","4151.T","4506.T","4536.T","4911.T","4565.T","4571.T",
    "4587.T","7733.T","7741.T","6849.T","7729.T","6954.T","6861.T",
    # 電機・精密
    "6758.T","6501.T","6702.T","6701.T","7751.T","6902.T","6954.T",
    "6367.T","6762.T","6988.T","6981.T","6645.T","6506.T","6504.T",
    "6508.T","6586.T","6727.T","6770.T","6803.T","7004.T","6952.T",
    "6301.T","6302.T","6361.T","6383.T",
    # 不動産
    "8801.T","8802.T","3289.T","8830.T","8804.T","8803.T","8818.T",
    "3231.T","8848.T","3279.T","3308.T","3234.T","8951.T","8952.T",
    "8953.T","8954.T","8955.T","8960.T","8972.T","8984.T","8985.T",
    # 通信・IT
    "9432.T","9433.T","9984.T","9437.T","9613.T","9719.T","4307.T",
    "3659.T","4385.T","3769.T","4686.T","3668.T","2432.T","4755.T",
    # 食品・消費
    "2914.T","2802.T","2503.T","2502.T","2269.T","2897.T","2871.T",
    "2282.T","2002.T","2810.T","2201.T","2204.T","2206.T","2207.T",
    "2212.T","2270.T","2531.T","2579.T","2651.T","2702.T","3099.T",
    "3197.T","8233.T","8252.T","9831.T","9830.T",
    # 小売
    "3382.T","3048.T","2670.T","8273.T","2651.T","9843.T","8267.T",
    "3099.T","8233.T","2670.T","3086.T","2659.T","3092.T","3141.T",
    # 観光・エンタメ・ゲーム
    "9602.T","7974.T","9684.T","3765.T","9766.T","9697.T","3635.T",
    "2121.T","3656.T","3668.T","3911.T","9001.T","9007.T","9008.T",
    "9009.T","9022.T","9020.T","9021.T","9006.T","9603.T",
    # 防衛・重工
    "7011.T","7012.T","7013.T","6508.T","9735.T","6586.T","1721.T",
    # 脱炭素・エネルギー
    "9531.T","9502.T","9503.T","9501.T","9508.T","9517.T","5020.T",
    "1605.T","4208.T","6504.T","6516.T","7004.T","1820.T","1928.T",
    # 建設・インフラ
    "1801.T","1802.T","1803.T","1812.T","1925.T","1928.T","5631.T",
    # 化学・素材
    "4063.T","4004.T","4005.T","4021.T","4041.T","4042.T","4208.T",
    "3407.T","4062.T","4186.T","5110.T","6988.T","4901.T",
    # 海運・空運
    "9101.T","9104.T","9107.T","9202.T","9201.T",
]

# 重複除去
PRIME_500 = list(dict.fromkeys(PRIME_500))
log.info(f"対象銘柄数: {len(PRIME_500)}")

# ===== キャッシュ =====
cache = {
    "prices": {},
    "updated_at": None,
    "status": "initializing"
}
cache_lock = threading.Lock()


def fetch_all_prices():
    """yfinanceで全銘柄一括取得"""
    try:
        import yfinance as yf
        import pandas as pd
    except ImportError:
        log.error("yfinance未インストール")
        return {}

    result = {}
    symbols = PRIME_500.copy()

    log.info(f"株価取得開始: {len(symbols)}銘柄")

    # 100銘柄ずつバッチ処理
    batch_size = 100
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i+batch_size]
        try:
            df = yf.download(
                batch,
                period="5d",
                interval="1d",
                auto_adjust=True,
                progress=False,
                threads=True,
                timeout=30,
            )
            if df.empty:
                continue

            close  = df["Close"].dropna(how="all").tail(2)
            volume = df["Volume"].dropna(how="all").tail(1)

            if len(close) < 2:
                continue

            prev_row = close.iloc[-2]
            last_row = close.iloc[-1]
            vol_row  = volume.iloc[-1] if not volume.empty else pd.Series()

            for sym in batch:
                try:
                    price = float(last_row[sym]) if sym in last_row.index else None
                    prev  = float(prev_row[sym]) if sym in prev_row.index else None
                    if price is None or prev is None:
                        continue
                    if pd.isna(price) or pd.isna(prev) or price == 0:
                        continue
                    vol    = float(vol_row[sym]) if sym in vol_row.index else 0
                    change = price - prev
                    pct    = (change / prev * 100) if prev else 0
                    result[sym] = {
                        "price":     round(price, 1),
                        "change":    round(change, 1),
                        "changePct": round(pct, 2),
                        "volume":    int(vol) if not pd.isna(vol) else 0,
                    }
                except Exception:
                    continue

            log.info(f"バッチ {i//batch_size+1}: {len(result)}銘柄取得済み")
        except Exception as e:
            log.error(f"バッチエラー: {e}")
            continue

    # 日経平均・為替は個別取得
    for sym in ["^N225", "USDJPY=X"]:
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="5d", interval="1d", auto_adjust=True)
            if len(hist) >= 2:
                price  = float(hist["Close"].iloc[-1])
                prev   = float(hist["Close"].iloc[-2])
                change = price - prev
                pct    = (change / prev * 100) if prev else 0
                result[sym] = {
                    "price":     round(price, 1),
                    "change":    round(change, 1),
                    "changePct": round(pct, 2),
                    "volume":    0,
                }
                log.info(f"✓ {sym}: {price:,.1f}")
        except Exception as e:
            log.warning(f"{sym}: {e}")

    log.info(f"✓ 合計 {len(result)} 銘柄取得完了")
    return result


def refresh_loop():
    """初回取得 + 30分ごとに自動更新"""
    while True:
        with cache_lock:
            cache["status"] = "updating"

        data = fetch_all_prices()

        with cache_lock:
            if data:
                cache["prices"] = data
                cache["updated_at"] = datetime.now().isoformat()
                cache["status"] = "ok"
            else:
                cache["status"] = "error"

        time.sleep(1800)  # 30分


# ===== API =====
@app.route("/api/prices")
def api_prices():
    with cache_lock:
        return jsonify({
            "prices":     cache["prices"],
            "updated_at": cache["updated_at"],
            "count":      len(cache["prices"]),
            "status":     cache["status"],
        })

@app.route("/api/status")
def api_status():
    with cache_lock:
        return jsonify({
            "ok":         cache["status"] == "ok",
            "status":     cache["status"],
            "count":      len(cache["prices"]),
            "updated_at": cache["updated_at"],
        })

@app.route("/api/quote/<symbol>")
def api_quote(symbol):
    """個別銘柄取得（キャッシュになければリアルタイム取得）"""
    sym = symbol.upper()
    if not sym.endswith(".T"):
        sym = sym + ".T"

    with cache_lock:
        if sym in cache["prices"]:
            return jsonify({"symbol": sym, **cache["prices"][sym]})

    # キャッシュになければ個別取得
    try:
        import yfinance as yf
        t = yf.Ticker(sym)
        hist = t.history(period="5d", interval="1d", auto_adjust=True)
        if len(hist) >= 2:
            price  = float(hist["Close"].iloc[-1])
            prev   = float(hist["Close"].iloc[-2])
            change = price - prev
            pct    = (change / prev * 100) if prev else 0
            return jsonify({
                "symbol":    sym,
                "price":     round(price, 1),
                "change":    round(change, 1),
                "changePct": round(pct, 2),
                "volume":    int(hist["Volume"].iloc[-1]),
            })
    except Exception as e:
        pass

    return jsonify({"error": "取得できませんでした"}), 404

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    if path and os.path.exists(os.path.join("static", path)):
        return send_from_directory("static", path)
    return send_from_directory("static", "index.html")


if __name__ == "__main__":
    # バックグラウンドで株価取得開始
    t = threading.Thread(target=refresh_loop, daemon=True)
    t.start()

    port = int(os.environ.get("PORT", 5050))
    log.info(f"サーバー起動: http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
