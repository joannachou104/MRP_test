"""解析上傳的 Excel / CSV 檔案為 list[dict]。"""
import io
import pandas as pd
from fastapi import UploadFile, HTTPException


def parse_upload_to_rows(file: UploadFile, content: bytes) -> list[dict]:
    filename = (file.filename or "").lower()
    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content), dtype=str)
        elif filename.endswith(".xlsx") or filename.endswith(".xls"):
            df = pd.read_excel(io.BytesIO(content), dtype=str)
        else:
            raise HTTPException(status_code=400, detail="僅支援 .csv / .xlsx 檔案格式")
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"檔案解析失敗: {exc}") from exc

    df = df.where(pd.notnull(df), None)
    rows = df.to_dict(orient="records")
    # 欄名去除前後空白
    cleaned_rows = [{(k.strip() if isinstance(k, str) else k): v for k, v in row.items()} for row in rows]
    return cleaned_rows
