from flask import Flask, render_template, request, redirect, url_for, flash
import os
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, bcrypt, User, Product  
from models import Cart, CartItem  


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///eco_exchange.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


db.init_app(app)
bcrypt.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.route('/')
def home():
    products = Product.query.all()  
    return render_template('home.html', products=products)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please log in.', 'danger')
            return redirect(url_for('register'))  

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, email=email, password=hashed_password)

        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))  

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('home'))  

        flash('Invalid email or password', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/sell', methods=['GET', 'POST'])
@login_required
def sell():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        image = request.files['image']  

        image_url = None
        if image:
            filename = secure_filename(image.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(filepath)
            image_url = f'static/uploads/{filename}'  

        product = Product(
            name=name, description=description, price=price,
            image_url=image_url, user_id=current_user.id
        )
        db.session.add(product)
        db.session.commit()

        flash('Product listed successfully!', 'success')
        return redirect(url_for('home'))

    return render_template('sell.html')

@app.route("/add_to_cart/<int:product_id>", methods=["POST"])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    
    # Find or create a cart for the user
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart:
        cart = Cart(user_id=current_user.id)
        db.session.add(cart)
        db.session.commit()  # Ensure cart exists before adding items

    # Find or create the cart item
    cart_item = CartItem.query.filter_by(cart_id=cart.id, product_id=product.id).first()
    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = CartItem(cart_id=cart.id, product_id=product.id, quantity=1)
        db.session.add(cart_item)

    db.session.commit()
    flash("Item added to cart!", "success")
    return redirect(url_for("my_cart"))



@app.route("/my_cart")
@login_required
def my_cart():
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    total_price = sum(item.product.price * item.quantity for item in cart.items if item.product)  # Ensure product exists
    return render_template("my_cart.html", cart=cart, total_price=total_price)



@app.route('/remove_from_cart/<int:product_id>', methods=['POST'])
@login_required
def remove_from_cart(product_id):
    cart = Cart.query.filter_by(user_id=current_user.id).first()

    if not cart:
        flash("Your cart is empty.", "info")
        return redirect(url_for('my_cart'))

    cart_item = CartItem.query.filter_by(cart_id=cart.id, product_id=product_id).first()

    if cart_item:
        db.session.delete(cart_item)
        db.session.commit()
        flash("Item removed from cart.", "success")

    return redirect(url_for('my_cart'))

@app.route("/checkout")
@login_required
def checkout():
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    
    if not cart or not cart.items:
        flash("Your cart is empty!", "warning")
        return redirect(url_for("cart_page"))  # Redirect back to the cart page

    # Clear cart after checkout (assuming order is processed)
    for item in cart.items:
        db.session.delete(item)

    db.session.commit()
    
    flash("Order confirmed!", "success")
    return redirect(url_for("home"))  # Redirect to homepage after checkout





@app.route('/delete/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)

    # Ensure only the owner can delete the product
    if product.user_id != current_user.id:
        flash("You are not authorized to delete this product.", "danger")
        return redirect(url_for('home'))

    # Remove the image file if necessary
    if product.image_url:
        image_path = os.path.join(app.root_path, product.image_url)
        if os.path.exists(image_path):
            os.remove(image_path)

    # Delete product from the database
    db.session.delete(product) 
    db.session.commit()

    flash("Product deleted successfully!", "success")
    return redirect(url_for('home'))


@app.route('/buy/<int:product_id>', methods=['GET'])
@login_required
def buy(product_id):
    product = Product.query.get_or_404(product_id)
    flash('Your order has been placed successfully!', 'success')
    return render_template('order_confirmation.html', product=product)  


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)