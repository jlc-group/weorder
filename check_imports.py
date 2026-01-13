import sys
print("Start check")
try:
    print("Importing webhooks...")
    from app.api.webhooks import webhook_router
    print("Webhooks OK")
    
    print("Importing integrations...")
    from app.api.integrations import integrations_router
    print("Integrations OK")

    print("Importing invoice_request...")
    from app.api.invoice_request import invoice_request_router
    print("Invoice Request OK")

    print("Importing finance...")
    from app.api.finance import finance_router
    print("Finance OK")

    print("Importing prepack...")
    from app.api.prepack import router as prepack_router
    print("Prepack OK")

    print("Importing reporting...")
    from app.api.reporting import router as reporting_router
    print("Reporting OK")

    print("Importing product_set...")
    from app.api.product_set import router as product_set_router
    print("Product Set OK")

    print("Importing listings...")
    from app.api.endpoints import listings as listings_router
    print("Listings OK")

    print("ALL IMPORTS OK")
except Exception as e:
    print(f"ERROR: {e}")
except KeyboardInterrupt:
    print("INTERRUPTED")
