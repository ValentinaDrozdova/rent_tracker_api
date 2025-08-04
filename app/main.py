from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import io
import re

app = FastAPI(
    title="Rent Payment Tracker API",
    description="API для отслеживания оплат аренды по платежным циклам и генерации отчетов.",
    version="1.0.0"
)


def get_next_due_date(start_date: datetime, all_payments: pd.DataFrame) -> datetime:
    """
    Рассчитывает следующую дату платежа на основе последнего платежа или стартовой даты.
    """
    if not all_payments.empty:
        last_payment_date = all_payments['date'].max()
        next_due_date_base = last_payment_date + relativedelta(months=1)

        try:
            return next_due_date_base.replace(day=start_date.day)
        except ValueError:
            last_day_of_month = (next_due_date_base.replace(day=1) + relativedelta(months=1) - timedelta(days=1)).day
            return next_due_date_base.replace(day=last_day_of_month)
    else:
        return start_date


def process_payment_files(rent_file: io.BytesIO, bank_statement_file: io.BytesIO) -> pd.DataFrame:
    """
    Основная логика обработки файлов.
    """
    try:
        arenda_df = pd.read_excel(rent_file, engine='openpyxl')
        arenda_df.columns = ['garage_name', 'amount', 'start_date']
        arenda_df['amount'] = pd.to_numeric(arenda_df['amount'], errors='coerce')
        arenda_df['start_date'] = pd.to_datetime(arenda_df['start_date'], errors='coerce')
        arenda_df.dropna(subset=['amount', 'start_date'], inplace=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка при чтении файла аренды: {e}")

    transactions = []
    try:
        statement_df = pd.read_excel(bank_statement_file, engine='openpyxl', header=None)
        for index, row in statement_df.iterrows():
            line_str = ' '.join([str(item) for item in row.values if pd.notna(item)])
            match = re.search(r'(\d{2}\.\d{2}\.\d{4}).*?(\+\s*[\d\s,]+\.\d{2})', line_str)
            if match:
                date_str, amount_str = match.groups()
                amount_clean_str = amount_str.replace('+', '').replace(' ', '').replace(',', '')
                amount_value = float(amount_clean_str)
                transactions.append({'date': pd.to_datetime(date_str, format='%d.%m.%Y'), 'paid_amount': amount_value})
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка при чтении банковской выписки: {e}")

    if transactions:
        payments_df = pd.DataFrame(transactions)
        payments_df['date'] = pd.to_datetime(payments_df['date'])
        payments_df['paid_amount'] = payments_df['paid_amount'].astype(float)
    else:
        payments_df = pd.DataFrame({
            'date': pd.Series(dtype='datetime64[ns]'),
            'paid_amount': pd.Series(dtype='float')
        })

    results = []
    today = datetime.now()

    for _, row in arenda_df.iterrows():
        garage_payments = payments_df[payments_df['paid_amount'] == row['amount']]

        due_date = get_next_due_date(row['start_date'], garage_payments)
        deadline = due_date + timedelta(days=3)

        status = ''
        if today < due_date:
            status = 'срок не наступил'
        elif due_date <= today <= deadline:
            status = 'ожидается оплата'
        else:
            status = 'просрочен'

        results.append({
            'Название гаража': row['garage_name'],
            'Дата оплаты (ожидаемая)': deadline.strftime('%Y-%m-%d'),
            'Сумма оплаты': row['amount'],
            'Статус': status
        })

    return pd.DataFrame(results)


@app.post("/generate_report/",
          summary="Сгенерировать отчет по оплатам",
          description="Загрузите XLSX-файлы с данными по аренде и банковской выпиской. Сервис найдет последний платеж и рассчитает следующий крайний срок.")
async def generate_report(
        rent_file: UploadFile = File(..., description="XLSX-файл с данными по аренде."),
        bank_statement_file: UploadFile = File(..., description="XLSX-файл с банковской выпиской.")
):
    if not rent_file.filename.endswith('.xlsx') or not bank_statement_file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="Допускаются только файлы формата .xlsx")

    try:
        rent_data = await rent_file.read()
        bank_data = await bank_statement_file.read()
        report_df = process_payment_files(io.BytesIO(rent_data), io.BytesIO(bank_data))
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            report_df.to_excel(writer, index=False, sheet_name='Payment Status')
        output.seek(0)
        headers = {'Content-Disposition': 'attachment; filename="payment_status_report.xlsx"'}
        return StreamingResponse(output, headers=headers,
                                 media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {e}")
