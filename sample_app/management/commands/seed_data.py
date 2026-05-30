import random
import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from sample_app.models import Category, Product, Customer, Order


CATEGORIES = ['Electrónica', 'Ropa', 'Hogar', 'Deportes', 'Libros', 'Juguetes', 'Alimentos']

PRODUCTS = [
    ('Laptop Pro 15"', 'Electrónica', 1299.99),
    ('Teclado Mecánico', 'Electrónica', 89.99),
    ('Monitor 27"', 'Electrónica', 349.00),
    ('Mouse Inalámbrico', 'Electrónica', 39.99),
    ('Auriculares BT', 'Electrónica', 129.99),
    ('Camiseta Básica', 'Ropa', 19.99),
    ('Pantalón Jean', 'Ropa', 59.99),
    ('Zapatillas Running', 'Ropa', 89.99),
    ('Chaqueta Invierno', 'Ropa', 149.99),
    ('Silla Ergonómica', 'Hogar', 299.00),
    ('Mesa de Escritorio', 'Hogar', 199.00),
    ('Lámpara LED', 'Hogar', 49.99),
    ('Cafetera Express', 'Hogar', 159.99),
    ('Pelota Fútbol', 'Deportes', 34.99),
    ('Pesas 10kg', 'Deportes', 44.99),
    ('Bicicleta Estática', 'Deportes', 399.00),
    ('Raqueta Tenis', 'Deportes', 79.99),
    ('Python Avanzado', 'Libros', 29.99),
    ('Django para Todos', 'Libros', 34.99),
    ('Clean Code', 'Libros', 39.99),
    ('Auto Lego 500pz', 'Juguetes', 59.99),
    ('Muñeca Articulada', 'Juguetes', 24.99),
    ('Set de Pinturas', 'Juguetes', 19.99),
    ('Granola Orgánica', 'Alimentos', 12.99),
    ('Café Premium 500g', 'Alimentos', 18.99),
]

CUSTOMERS = [
    ('Ana García', 'ana@example.com', 'Asunción'),
    ('Carlos López', 'carlos@example.com', 'Ciudad del Este'),
    ('María Fernández', 'maria@example.com', 'Encarnación'),
    ('José Martínez', 'jose@example.com', 'Asunción'),
    ('Laura Rodríguez', 'laura@example.com', 'Luque'),
    ('Pedro Sánchez', 'pedro@example.com', 'Fernando de la Mora'),
    ('Sofia Gómez', 'sofia@example.com', 'San Lorenzo'),
    ('Diego Torres', 'diego@example.com', 'Capiatá'),
    ('Valentina Ruiz', 'valentina@example.com', 'Lambaré'),
    ('Andrés Flores', 'andres@example.com', 'Asunción'),
    ('Camila Díaz', 'camila@example.com', 'Villarrica'),
    ('Lucas Moreno', 'lucas@example.com', 'Coronel Oviedo'),
]

STATUSES = ['pending', 'confirmed', 'shipped', 'delivered', 'cancelled']


class Command(BaseCommand):
    help = 'Poblar la base de datos con datos de ejemplo'

    def handle(self, *args, **options):
        self.stdout.write('Limpiando datos anteriores...')
        Order.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()
        Customer.objects.all().delete()

        self.stdout.write('Creando categorías...')
        cats = {}
        for name in CATEGORIES:
            cats[name] = Category.objects.create(name=name, slug=slugify(name))

        self.stdout.write('Creando productos...')
        products = []
        for name, cat_name, price in PRODUCTS:
            p = Product.objects.create(
                name=name,
                price=Decimal(str(price)),
                stock=random.randint(0, 150),
                category=cats[cat_name],
                active=random.random() > 0.1,
            )
            products.append(p)

        self.stdout.write('Creando clientes...')
        customers = []
        for name, email, city in CUSTOMERS:
            c = Customer.objects.create(name=name, email=email, city=city)
            customers.append(c)

        self.stdout.write('Creando órdenes...')
        today = datetime.date.today()
        for _ in range(80):
            customer = random.choice(customers)
            product = random.choice(products)
            quantity = random.randint(1, 5)
            total = product.price * quantity
            days_ago = random.randint(0, 180)
            Order.objects.create(
                customer=customer,
                product=product,
                quantity=quantity,
                total=total,
                status=random.choice(STATUSES),
                date=today - datetime.timedelta(days=days_ago),
            )

        self.stdout.write(self.style.SUCCESS(
            f'OK: {len(CATEGORIES)} categorías, {len(products)} productos, '
            f'{len(customers)} clientes, 80 órdenes.'
        ))
