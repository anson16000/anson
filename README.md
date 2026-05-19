# 鍚屽煄閰嶉€佺粡钀ュ垎鏋愮郴缁?
鍩轰簬 `Python + FastAPI + DuckDB + Power BI/缃戦〉鐪嬫澘` 鐨勬湰鍦伴厤閫佺粡钀ュ垎鏋愮郴缁熴€?
褰撳墠鏁版嵁閾捐矾锛?
```text
鍘熷璁㈠崟/鍚嶅崟鏂囦欢
-> Python 瀵煎叆
-> DuckDB ODS/DWD/ADS
-> 缃戦〉鐪嬫澘
-> Power BI Parquet 鎴愬搧灞?```

## 椤甸潰鍏ュ彛

| 椤甸潰 | 璺敱 | 璇存槑 |
| --- | --- | --- |
| 鍏ㄥ浗鎬昏 | `/` | 鍏ㄥ浗绾х粡钀ユ瑙堛€佽秼鍔裤€佹帓鍚嶅拰鍒嗗眰 |
| 鍩庡競缁忚惀 | `/partner` | 鍗曞煄甯傜粡钀ユ憳瑕併€佹敹鐩婂拰鐩磋惀涓撻」鍏ュ彛 |
| 鏃舵鐑姏涓庡饱绾?| `/partner/hourly` | 灏忔椂杩愬姏銆佺儹鍔涖€佸饱绾︿笌 SLA |
| 涓讳綋鍒嗘瀽 | `/partner/entities` | 鍟嗘埛銆侀獞鎵嬨€佷富浣撹瘑鍒笌鍚嶅崟鏄庣粏 |
| 璇婃柇棰勮 | `/alerts` | 椋庨櫓銆佸叧娉ㄣ€佸仴搴峰害涓庢尝鍔ㄩ璀?|

鍏煎鍏ュ彛锛?
- `/direct` 浼氳烦杞埌 `/partner?section=direct`

## Windows 棣栨閮ㄧ讲

褰撳墠椤圭洰涓昏鏀寔 Windows 鏈湴浣跨敤銆?
1. 澶嶅埗鏁翠釜椤圭洰鐩綍鍒版柊鐢佃剳銆?2. 鍙屽嚮杩愯 `00-鍒濆鍖栫幆澧?bat`銆?3. 鍒濆鍖栨垚鍔熷悗锛屽弻鍑?`02-涓€閿惎鍔ㄧ湅鏉?bat`銆?4. 濡傞渶瀵煎叆鏁版嵁锛岃繍琛?`01-涓€閿鍏ユ暟鎹?bat`銆?5. 濡備唬鐮侀€昏緫淇繃浣嗗師濮嬫枃浠舵病鍙橈紝杩愯 `01-涓€閿己鍒堕噸寤?bat`銆?
鍒濆鍖栬剼鏈細鑷姩锛?
- 妫€鏌?Python 3.12銆?- 鍒涘缓 `.venv`銆?- 瀹夎 `requirements.txt`銆?- 妫€鏌ョ洰褰曘€侀厤缃拰绔彛銆?
## 甯哥敤鍛戒护

```powershell
# 鏅€氬鍏ワ紝鏂囦欢鏈彉鍖栨椂浼氳烦杩?python main.py import --mode=auto

# 寮哄埗閲嶅缓锛屽拷鐣ユ枃浠跺幓閲?python main.py import --mode=force

# 鍙鍑?Power BI Parquet 鎴愬搧灞?python main.py export-powerbi

# 鍚姩缃戦〉鐪嬫澘
python main.py server --port 8090

# 杩愯娴嬭瘯
python -m unittest discover -s tests -p "test*.py"
```

## 甯哥敤鎵瑰鐞嗚剼鏈?
| 鑴氭湰 | 浣滅敤 |
| --- | --- |
| `00-鍒濆鍖栫幆澧?bat` | 棣栨閮ㄧ讲銆佺幆澧冩鏌ヤ笌鑷姩瀹夎 |
| `01-涓€閿鍏ユ暟鎹?bat` | 鏅€氬鍏ユ暟鎹?|
| `01-涓€閿己鍒堕噸寤?bat` | 寮哄埗閲嶅缓褰撳墠鏂囦欢瀵瑰簲鏈堜唤 |
| `02-涓€閿惎鍔ㄧ湅鏉?bat` | 鍚姩鏈湴缃戦〉鐪嬫澘 |
| `03-杩愯娴嬭瘯.bat` | 杩愯鑷姩鍖栨祴璇?|
| `04-瀵煎嚭PowerBI-Parquet.bat` | 鎵嬪姩瀵煎嚭 Power BI Parquet 鎴愬搧灞?|

## Power BI Parquet 鎴愬搧灞?
瀵煎叆鎴愬姛鍚庝細鑷姩瀵煎嚭锛?
```text
exports/powerbi_parquet/
```

Power BI 寤鸿璇诲彇杩欎簺 Parquet 鏂囦欢锛岃€屼笉鏄洿鎺ヨ繛鎺?DuckDB 鏁版嵁搴撴枃浠躲€?
杩欐牱鍙互鍑忓皯锛?
- DuckDB 鏂囦欢閿併€?- ODBC 椹卞姩闂銆?- Power BI 鍒锋柊鍗犵敤鏁版嵁搴撱€?- 澶氱數鑴戣矾寰勪笉涓€鑷淬€?
鎵嬪姩瀵煎嚭锛?
```powershell
python main.py export-powerbi
```

鎴栧弻鍑伙細

```text
04-瀵煎嚭PowerBI-Parquet.bat
```

璇︾粏璇存槑瑙侊細

- `docs/Python+DuckDB+Parquet+PowerBI閲嶆瀯鏂规.md`

## 鏁版嵁鐩綍

```text
data/
鈹溾攢 orders_raw/      # 鍘熷璁㈠崟鏁版嵁
鈹溾攢 orders_stage/    # 璁㈠崟棰勫鐞嗗悗鐨?stage 鏂囦欢
鈹溾攢 orders/          # 鍏煎鏃х洰褰?鈹溾攢 riders/          # 楠戞墜/甯墜鍚嶅崟
鈹溾攢 merchants/       # 鍟嗗/鍟嗘埛鍚嶅崟
鈹斺攢 partners/        # 鍚堜紮浜哄悕鍗?```

棣栨閮ㄧ讲鏃?`data/` 鍙互涓虹┖銆傛病鏈変笟鍔℃暟鎹椂锛岄〉闈㈠彲鍚姩锛屼絾涓嶄細鏄剧ず鐪熷疄涓氬姟缁撴灉銆?
## GitHub 涓婁紶杈圭晫

浠撳簱鍙笂浼犱唬鐮佸拰鏂囨。锛屼笉涓婁紶涓氬姟鍘熷鏁版嵁鍜岀敓鎴愮粨鏋溿€?
榛樿涓嶄笂浼狅細

- `data/`
- `db/*.duckdb`
- `db/*.duckdb.wal`
- `logs/`
- `exports/`

## 鏂囨。

涓昏鏂囨。鍦?`docs/` 鐩綍锛?
- `Python+DuckDB+Parquet+PowerBI閲嶆瀯鏂规.md`
- `Python+DuckDB+PowerBI鐩磋繛閲嶆瀯鏂规.md`
- `ODS-DWD-ADS鐜版湁琛ㄨ鏄?md`
- `ODS-DWD-ADS琛ㄧ敓鎴愭祦绋嬭鏄?md`
- `鍚屽煄閰嶉€佺粡钀ュ垎鏋愮郴缁?瀛楁瀛楀吀-v1.md`
- `鍚屽煄閰嶉€佺粡钀ュ垎鏋愮郴缁?椤圭洰瀹屾暣鍙ｅ緞鎵嬪唽-v1.md`

## 榛樿绔彛

缃戦〉鐪嬫澘榛樿绔彛锛?
```text
8090
```
