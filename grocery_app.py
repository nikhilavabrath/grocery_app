import mysql.connector
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np

# 🔧 Added: Define today's date globally
today = datetime.now().date()

# ---------------------------
# Database connection
# ---------------------------
conn = mysql.connector.connect(
	host="localhost",
	user="root",
	password="1234",
	database="grocery_db"
)
cursor = conn.cursor()

# ---------------------------
# Table setup
# ---------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
	product_id INT PRIMARY KEY,
	name VARCHAR(50),
	price FLOAT,
	stock INT,
	brand VARCHAR(50) DEFAULT 'Generic',
	quantity VARCHAR(30) DEFAULT '200 g - Cup',
	image VARCHAR(100) DEFAULT 'default.jpg'
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS customers (
	customer_id INT PRIMARY KEY,
	name VARCHAR(50),
	phone VARCHAR(15)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
	order_id INT AUTO_INCREMENT PRIMARY KEY,
	customer_id INT,
	order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS order_items (
	order_id INT,
	product_id INT,
	quantity INT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS nudges (
	nudge_id INT AUTO_INCREMENT PRIMARY KEY,
	customer_id INT,
	product_id INT,
	nudge_date DATE,
	confidence FLOAT,
	status VARCHAR(20) DEFAULT 'pending'
)
""")

# ---------------------------
# Core Functions
# ---------------------------

def view_products():
	cursor.execute("SELECT * FROM products")
	for row in cursor.fetchall():
		print(row)

def place_order():
	customer_id = input("Enter customer ID: ")
	cursor.execute("INSERT INTO orders (customer_id) VALUES (%s)", (customer_id,))
	order_id = cursor.lastrowid

	while True:
		try:
			product_id = int(input("Enter product ID (0 to finish): "))
		except ValueError:
			print("❌ Please enter a valid number.")
			continue

		if product_id == 0:
			break

		qty = int(input("Enter quantity: "))

		cursor.execute("SELECT stock FROM products WHERE product_id=%s", (product_id,))
		result = cursor.fetchone()

		if result and result[0] >= qty:
			cursor.execute("UPDATE products SET stock = stock - %s WHERE product_id=%s", (qty, product_id))
			cursor.execute(
				"INSERT INTO order_items (order_id, product_id, quantity) VALUES (%s, %s, %s)",
				(order_id, product_id, qty)
			)
			conn.commit()
			print("✅ Item added to order!")
		else:
			print("⚠️ Not enough stock available.")

		cursor.execute("""
			UPDATE nudges
			SET status = 'resolved'
			WHERE customer_id = %s AND product_id = %s AND status = 'pending'
		""", (customer_id, product_id))
		conn.commit()

def view_low_stock():
	cursor.execute("SELECT * FROM products WHERE stock < 5")
	low_stock_items = cursor.fetchall()
	if not low_stock_items:
		print("👍 All products are sufficiently stocked.")
	else:
		print("⚠️ Low Stock Alerts:")
		for row in low_stock_items:
			print(row)

def predict_reorders(customer_id):
	cursor.execute("""
		SELECT 
			product_id,
			o.order_date
		FROM order_items oi
		JOIN orders o ON oi.order_id = o.order_id
		WHERE o.customer_id = %s
		ORDER BY oi.product_id, o.order_date
	""", (customer_id,))
	
	rows = cursor.fetchall()
	if not rows:
		print("❌ No purchase history for this customer yet.")
		return

	product_orders = defaultdict(list)
	for product_id, order_date in rows:
		product_orders[product_id].append(order_date)

	basket = defaultdict(list)

	avg_gaps_dict = {}
	last_orders_dict = {}
	reorder_days_dict = {}
	confidence_scores = {}

	def calculate_confidence(avg_gap, days_since_last_order):
		ratio = days_since_last_order / avg_gap
		confidence = max(0.0, min(1.0, ratio))
		return round(confidence, 2)

	for product_id, dates in product_orders.items():
		if len(dates) < 2:
			print(f"📦 Product {product_id} purchased once, not enough data for prediction.")
			continue

		gaps = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]
		avg_gap = sum(gaps) / len(gaps)
		std_dev = np.std(gaps)

		last_order = dates[-1]
		next_expected = last_order + timedelta(days=int(avg_gap))

		cursor.execute("SELECT name, price, stock FROM products WHERE product_id = %s", (product_id,))
		name, price, stock = cursor.fetchone()

		print(f"\n📦 {name} (Product ID {product_id}):")
		print(f"   Bought {len(dates)} times, avg gap {avg_gap:.1f} days")
		print(f"   Last order: {last_order}")
		print(f"   ⏭️ Next expected reorder: {next_expected.date()}")

		days_since_last = (today - last_order.date()).days
		days_until = (next_expected.date() - today).days

		avg_gaps_dict[name] = avg_gap
		last_orders_dict[name] = last_order.date()
		reorder_days_dict[name] = days_until

		confidence = calculate_confidence(avg_gap, days_since_last)
		confidence_scores[name] = confidence

		print(f"   🔍 Confidence Score: {confidence}")
		print(f"🧠 Debug: {name} → Days until: {days_until}, Confidence: {confidence:.2f}")

		cursor.execute("""
			INSERT INTO nudges (customer_id, product_id, nudge_date, confidence)
			VALUES (%s, %s, %s, %s)
		""", (customer_id, product_id, next_expected.date(), confidence))
		conn.commit()

		basket[next_expected.date()].append(name)

	for name in reorder_days_dict:
		days_until = reorder_days_dict[name]
		confidence = confidence_scores[name]

		if days_until <= 0:
			trigger_nudge = True
		elif days_until <= 2 and confidence >= 0.6:
			trigger_nudge = True
		else:
			trigger_nudge = False

		if trigger_nudge:
			print(f"🔔 Hey Nikhil, you're probably running low on {name}.")
			response = input(f"👉 Would you like to reorder {name}? (Y/N): ").strip().lower()

			if response == 'y':
				while True:
					try:
						qty = int(input(f"🧮 How many units of {name} would you like to order?: "))
						if qty <= 0:
							print("❌ Quantity must be positive.")
							continue
						if qty > stock:
							print(f"⚠️ Only {stock} units available in stock.")
							continue
						break
					except ValueError:
						print("❌ Please enter a valid number.")

				cursor.execute("INSERT INTO orders (customer_id) VALUES (%s)", (customer_id,))
				order_id = cursor.lastrowid
				cursor.execute("INSERT INTO order_items (order_id, product_id, quantity) VALUES (%s, %s, %s)",
							   (order_id, product_id, qty))
				cursor.execute("UPDATE products SET stock = stock - %s WHERE product_id = %s", (qty, product_id))
				cursor.execute("UPDATE nudges SET status = 'resolved' WHERE customer_id = %s AND product_id = %s AND status = 'pending'",
							   (customer_id, product_id))
				conn.commit()
				print(f"✅ Order placed for {qty} units of {name}. Nudge resolved!")
				print("🏆 Leaderboard will reflect this resolved nudge next time you view it.")

	if basket:
		print("\n🧺 Suggested Basket Groupings:")
		for date, items in basket.items():
			print(f"   📅 {date}: {', '.join(items)}")

def suggest_frequent_products(customer_id):
	cursor.execute("""
		SELECT product_id, COUNT(*) AS freq
		FROM order_items oi
		JOIN orders o ON oi.order_id = o.order_id
		WHERE o.customer_id = %s
		GROUP BY oi.product_id
		ORDER BY freq DESC
		LIMIT 3
	""", (customer_id,))
	
	suggestions = cursor.fetchall()
	if suggestions:
		print("🛍️ Frequently Ordered Products:")
		for pid, freq in suggestions:
			cursor.execute("SELECT name FROM products WHERE product_id = %s", (pid,))
			name = cursor.fetchone()[0]
			print(f"   {name} (Product ID {pid}) ordered {freq} times")

def show_leaderboard():
	cursor.execute("""
		SELECT 
			c.customer_id,
			c.name,
			COUNT(n.nudge_id) AS total_nudges,
			SUM(CASE WHEN n.status = 'resolved' THEN 1 ELSE 0 END) AS resolved_nudges,
			ROUND(SUM(CASE WHEN n.status = 'resolved' THEN 1 ELSE 0 END) / COUNT(n.nudge_id), 2) AS consistency_score		FROM customers c
		LEFT JOIN nudges n ON c.customer_id = n.customer_id
		GROUP BY c.customer_id
		HAVING COUNT(n.nudge_id) > 0
		ORDER BY consistency_score DESC, resolved_nudges DESC
		LIMIT 5
	""")
	
	leaderboard = cursor.fetchall()
	print("\n🏆 Most Consistent Customers:")
	for cid, name, total, resolved, score in leaderboard:
		print(f"   {name} (ID: {cid}) - {resolved}/{total} nudges resolved | Score: {score}")

# ---------------------------
# 🔧 Additional Enhancements
# ---------------------------

basket_preview = []

def add_to_basket():
	cursor.execute("SELECT * FROM products")
	products = cursor.fetchall()
	print("\n🛒 Available Products:")
	for p in products:
		print(f"{p[0]}. {p[1]} - ₹{p[2]} | Stock: {p[3]}")

	while True:
		try:
			pid = int(input("Enter product ID to add to basket (0 to finish): "))
			if pid == 0:
				break
			qty = int(input("Enter quantity: "))
			cursor.execute("SELECT name, stock FROM products WHERE product_id = %s", (pid,))
			result = cursor.fetchone()
			if not result:
				print("❌ Product not found.")
				continue
			name, stock = result
			if qty > stock:
				print(f"⚠️ Only {stock} units available.")
				continue
			basket_preview.append((pid, name, qty))
			print(f"✅ Added {qty} x {name} to basket.")
		except:
			print("❌ Invalid input. Try again.")

def view_basket():
	if not basket_preview:
		print("🧺 Basket is empty.")
	else:
		print("\n🧺 Basket Preview:")
		for pid, name, qty in basket_preview:
			print(f"   {qty} x {name} (Product ID {pid})")

def search_products():
	keyword = input("🔍 Enter product name or keyword: ").lower()
	cursor.execute("SELECT product_id, name, price, stock FROM products")
	results = cursor.fetchall()
	matches = [r for r in results if keyword in r[1].lower()]
	if matches:
		print("\n🔎 Search Results:")
		for pid, name, price, stock in matches:
			print(f"{pid}. {name} - ₹{price} | Stock: {stock}")
	else:
		print("❌ No matching products found.")

# ---------------------------
# Menu
# ---------------------------
while True:
	print("\n1. View Products")
	print("2. Place Order")
	print("3. View Low Stock Alerts")
	print("4. Predict Reorders for Customer")
	print("5. Suggest Frequent Products")
	print("6. Show Leaderboard")
	print("7. Exit")
	print("8. Add to Basket")
	print("9. View Basket")
	print("10. Search Products")

	choice = input("Choose an option: ")

	if choice == "1":
		view_products()
	elif choice == "2":
		place_order()
	elif choice == "3":
		view_low_stock()
	elif choice == "4":
		cid = input("Enter customer ID:")
		predict_reorders(cid)
	elif choice == "5":
		cid = input("Enter customer ID: ")
		suggest_frequent_products(cid)
	elif choice == "6":
		show_leaderboard()
	elif choice == "7":
		print("👋 Exiting... Have a great day!")
		break
	elif choice == "8":
		add_to_basket()
	elif choice == "9":
		view_basket()
	elif choice == "10":
		search_products()
	else:
		print("❌ Invalid choice. Try again.")

cursor.close()
conn.close()