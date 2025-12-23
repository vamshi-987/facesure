# config.py
class Config:
    MONGO_URI = "mongodb+srv://vamshivardhan987_db_user:yHa8P9nAfn5dMyss@cluster0.l4bjzcp.mongodb.net/faceAuthDB?retryWrites=true&w=majority&appName=Cluster0"
    JWT_SECRET = "SUPER_SECRET_KEY"

    SUPERADMINS = [
        {
            "_id": "superadmin",
            "password": "Super@123",
            "name": "Super Admin One",
            "phone": "9999999999"
        },
        {
            "_id": "superadmin2",
            "password": "Super@123",
            "name": "Super Admin Two",
            "phone": "8888888888"
        }
    ]
