from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from faker import Faker
import uuid
import json
import csv
import io
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import random
import os

app = FastAPI(
    title="Mock Data Generator API",
    description="Генератор тестовых данных по схеме — Users, Companies, Products, Transactions",
    version="2.0.0"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(BASE_DIR, "static")

if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# ── Faker instances ──────────────────────────────────────────────────────────
FAKERS = {
    'ru_RU': Faker('ru_RU'),
    'en_US': Faker('en_US'),
    'uk_UA': Faker('uk_UA'),
}

# ── Generators ───────────────────────────────────────────────────────────────

def generate_user(fake: Faker) -> dict:
    return {
        "id":         str(uuid.uuid4()),
        "name":       fake.name(),
        "email":      fake.email(),
        "phone":      fake.phone_number(),
        "address":    fake.address().replace('\n', ', '),
        "job":        fake.job(),
        "birthdate":  fake.date_of_birth(minimum_age=18, maximum_age=70).isoformat(),
        "created_at": fake.date_time_this_decade().isoformat(),
    }


def generate_company(fake: Faker) -> dict:
    return {
        "id":       str(uuid.uuid4()),
        "name":     fake.company(),
        "industry": random.choice([
            "IT", "Finance", "Healthcare", "Retail",
            "Manufacturing", "Education", "Logistics",
        ]),
        "email":    fake.company_email(),
        "phone":    fake.phone_number(),
        "address":  fake.address().replace('\n', ', '),
        "website":  fake.url(),
        "employees": random.randint(5, 10000),
        "revenue":  round(random.uniform(100_000, 50_000_000), 2),
        "founded":  fake.year(),
    }


def generate_product(fake: Faker) -> dict:
    categories = ["Electronics", "Clothing", "Books", "Food", "Sports", "Home", "Beauty"]
    price = round(random.uniform(1.99, 999.99), 2)
    return {
        "id":          str(uuid.uuid4()),
        "name":        fake.catch_phrase(),
        "sku":         fake.bothify(text="??-####-??").upper(),
        "category":    random.choice(categories),
        "price":       price,
        "sale_price":  round(price * random.uniform(0.7, 0.99), 2) if random.random() > 0.6 else None,
        "stock":       random.randint(0, 500),
        "rating":      round(random.uniform(1.0, 5.0), 1),
        "reviews":     random.randint(0, 2000),
        "in_stock":    random.random() > 0.15,
        "created_at":  fake.date_time_this_year().isoformat(),
    }


def generate_transaction(fake: Faker) -> dict:
    statuses = ["completed", "pending", "failed", "refunded"]
    methods  = ["card", "cash", "bank_transfer", "crypto", "paypal"]
    amount   = round(random.uniform(1.00, 5000.00), 2)
    return {
        "id":              str(uuid.uuid4()),
        "amount":          amount,
        "currency":        random.choice(["RUB", "USD", "EUR", "UAH"]),
        "status":          random.choice(statuses),
        "payment_method":  random.choice(methods),
        "sender":          fake.name(),
        "receiver":        fake.company(),
        "description":     fake.bs(),
        "timestamp":       fake.date_time_this_month().isoformat(),
        "fee":             round(amount * 0.015, 2),
    }


GENERATORS = {
    "users":        generate_user,
    "companies":    generate_company,
    "products":     generate_product,
    "transactions": generate_transaction,
}

# ── Custom JSON Schema generator ─────────────────────────────────────────────

def _fake_value(fake: Faker, field_schema: dict):
    t = field_schema.get("type", "string")
    fmt = field_schema.get("format", "")
    enum = field_schema.get("enum")

    if enum:
        return random.choice(enum)
    if t == "integer":
        return random.randint(
            field_schema.get("minimum", 0),
            field_schema.get("maximum", 1000),
        )
    if t == "number":
        return round(random.uniform(
            field_schema.get("minimum", 0.0),
            field_schema.get("maximum", 1000.0),
        ), 2)
    if t == "boolean":
        return random.random() > 0.5
    # string variants
    if fmt == "email":    return fake.email()
    if fmt == "uri":      return fake.url()
    if fmt == "date":     return fake.date().replace(" ", "-")
    if fmt == "datetime": return fake.date_time_this_decade().isoformat()
    if fmt == "uuid":     return str(uuid.uuid4())
    if fmt == "phone":    return fake.phone_number()
    if fmt == "name":     return fake.name()
    if fmt == "address":  return fake.address().replace('\n', ', ')
    if fmt == "company":  return fake.company()
    if fmt == "text":     return fake.text(max_nb_chars=200)
    # fallback
    return fake.word()


def generate_from_schema(fake: Faker, schema: dict) -> dict:
    """Generate one record matching the given JSON Schema (properties only)."""
    if schema.get("type") != "object" or "properties" not in schema:
        raise ValueError("Schema must be of type 'object' with 'properties'")
    record = {}
    for field, field_schema in schema["properties"].items():
        record[field] = _fake_value(fake, field_schema)
    return record


# ── Export helpers ────────────────────────────────────────────────────────────

def records_to_csv(records: list[dict]) -> str:
    if not records:
        return ""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=records[0].keys())
    writer.writeheader()
    writer.writerows(records)
    return buf.getvalue()


def records_to_xml(records: list[dict], root_tag: str = "records", item_tag: str = "record") -> str:
    root = ET.Element(root_tag)
    for rec in records:
        item = ET.SubElement(root, item_tag)
        for k, v in rec.items():
            child = ET.SubElement(item, str(k))
            child.text = "" if v is None else str(v)
    return ET.tostring(root, encoding="unicode", xml_declaration=False)


# ── Web UI ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def web_interface():
    html_path = os.path.join(BASE_DIR, "templates", "index.html")
    if os.path.exists(html_path):
        with open(html_path, encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h2>index.html not found</h2>", status_code=404)


# ── Standard endpoints ────────────────────────────────────────────────────────

@app.get("/api/{entity}")
async def get_entities(
    entity: str,
    count:  int = Query(5, ge=1, le=1000, description="Число записей"),
    locale: str = Query("ru_RU", description="Локаль: ru_RU, en_US, uk_UA"),
    format: str = Query("json", description="Формат: json, csv, xml"),
):
    """Генерация данных для стандартных схем: users, companies, products, transactions."""
    if entity not in GENERATORS:
        raise HTTPException(status_code=404, detail={
            "error": f"Unknown entity '{entity}'",
            "available": list(GENERATORS.keys()),
        })
    if locale not in FAKERS:
        raise HTTPException(status_code=400, detail={
            "error": f"Unknown locale '{locale}'",
            "available": list(FAKERS.keys()),
        })

    fake    = FAKERS[locale]
    gen_fn  = GENERATORS[entity]
    records = [gen_fn(fake) for _ in range(count)]

    if format == "csv":
        csv_data = records_to_csv(records)
        return StreamingResponse(
            io.StringIO(csv_data),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={entity}.csv"},
        )
    if format == "xml":
        xml_data = records_to_xml(records, root_tag=entity, item_tag=entity.rstrip("s"))
        return StreamingResponse(
            io.StringIO(xml_data),
            media_type="application/xml",
            headers={"Content-Disposition": f"attachment; filename={entity}.xml"},
        )

    # default: json
    return {
        "success": True,
        "entity":  entity,
        "count":   len(records),
        "locale":  locale,
        "data":    records,
    }


# ── Custom schema endpoint ────────────────────────────────────────────────────

@app.post("/api/custom")
async def generate_custom(
    body: dict,
    count:  int = Query(5, ge=1, le=1000),
    locale: str = Query("ru_RU"),
    format: str = Query("json"),
):
    """
    Генерация по произвольной JSON Schema.

    Пример тела запроса:
    ```json
    {
      "type": "object",
      "properties": {
        "id":      { "format": "uuid" },
        "name":    { "format": "name" },
        "score":   { "type": "integer", "minimum": 0, "maximum": 100 },
        "active":  { "type": "boolean" },
        "role":    { "enum": ["admin", "user", "guest"] }
      }
    }
    ```
    Поддерживаемые форматы строк: email, uri, date, datetime, uuid, phone, name, address, company, text.
    """
    if locale not in FAKERS:
        raise HTTPException(status_code=400, detail={"error": "Unknown locale"})
    fake = FAKERS[locale]
    try:
        records = [generate_from_schema(fake, body) for _ in range(count)]
    except ValueError as e:
        raise HTTPException(status_code=422, detail={"error": str(e)})

    if format == "csv":
        return StreamingResponse(
            io.StringIO(records_to_csv(records)),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=custom.csv"},
        )
    if format == "xml":
        return StreamingResponse(
            io.StringIO(records_to_xml(records)),
            media_type="application/xml",
            headers={"Content-Disposition": "attachment; filename=custom.xml"},
        )
    return {"success": True, "count": len(records), "locale": locale, "data": records}


# ── Meta endpoints ────────────────────────────────────────────────────────────

@app.get("/api/schema/{entity}")
async def get_schema(entity: str):
    """Возвращает JSON Schema для выбранной сущности."""
    schemas = {
        "users": {
            "type": "object",
            "properties": {
                "id":         {"format": "uuid"},
                "name":       {"format": "name"},
                "email":      {"format": "email"},
                "phone":      {"format": "phone"},
                "address":    {"format": "address"},
                "job":        {"type": "string"},
                "birthdate":  {"format": "date"},
                "created_at": {"format": "datetime"},
            }
        },
        "companies": {
            "type": "object",
            "properties": {
                "id":        {"format": "uuid"},
                "name":      {"format": "company"},
                "industry":  {"enum": ["IT","Finance","Healthcare","Retail","Manufacturing","Education","Logistics"]},
                "email":     {"format": "email"},
                "phone":     {"format": "phone"},
                "address":   {"format": "address"},
                "website":   {"format": "uri"},
                "employees": {"type": "integer", "minimum": 5, "maximum": 10000},
                "revenue":   {"type": "number", "minimum": 100000, "maximum": 50000000},
                "founded":   {"type": "integer", "minimum": 1900, "maximum": 2024},
            }
        },
        "products": {
            "type": "object",
            "properties": {
                "id":         {"format": "uuid"},
                "name":       {"type": "string"},
                "sku":        {"type": "string"},
                "category":   {"enum": ["Electronics","Clothing","Books","Food","Sports","Home","Beauty"]},
                "price":      {"type": "number", "minimum": 1.99, "maximum": 999.99},
                "stock":      {"type": "integer", "minimum": 0, "maximum": 500},
                "rating":     {"type": "number", "minimum": 1.0, "maximum": 5.0},
                "in_stock":   {"type": "boolean"},
                "created_at": {"format": "datetime"},
            }
        },
        "transactions": {
            "type": "object",
            "properties": {
                "id":             {"format": "uuid"},
                "amount":         {"type": "number", "minimum": 1.0, "maximum": 5000.0},
                "currency":       {"enum": ["RUB","USD","EUR","UAH"]},
                "status":         {"enum": ["completed","pending","failed","refunded"]},
                "payment_method": {"enum": ["card","cash","bank_transfer","crypto","paypal"]},
                "sender":         {"format": "name"},
                "receiver":       {"format": "company"},
                "timestamp":      {"format": "datetime"},
                "fee":            {"type": "number"},
            }
        },
    }
    if entity not in schemas:
        raise HTTPException(status_code=404, detail={"error": f"No schema for '{entity}'"})
    return schemas[entity]


@app.get("/health")
async def health():
    return {
        "status":    "healthy",
        "timestamp": datetime.now().isoformat(),
        "entities":  list(GENERATORS.keys()),
        "locales":   list(FAKERS.keys()),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)