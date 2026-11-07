web: cd backend && python db/init_db.py && gunicorn main:app -k uvicorn.workers.UvicornWorker -w 2 --timeout 300 -b 0.0.0.0:$PORT
