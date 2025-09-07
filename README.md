# 🛒 grocery_app

**Smart Grocery Reorder Assistant using Python and MySQL**

This script helps manage grocery inventory and triggers reorder alerts based on quantity thresholds. Designed for backend automation and database-driven logic — no frontend or web interface included.

---

## 🧠 Features

- Add, update, and delete grocery items
- Track item quantities and reorder levels
- MySQL database integration for persistent storage
- Simple, modular Python logic

---

## 🛠️ Tech Stack

- **Language**: Python 3.x
- **Database**: MySQL
- **Libraries**: `mysql.connector`

---

## ⚙️ Setup Instructions

1. Clone the repository:
  
   git clone https://github.com/nikhilbarath/grocery_app.git
   cd grocery_app
   
2. Install required Python package:
   
   pip install mysql-connector-python

3. Create a MySQL database and table:

   CREATE DATABASE grocery_db;

  USE grocery_db;

  CREATE TABLE groceries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    item_name VARCHAR(255),
    quantity INT,
    reorder_threshold INT
  );

4.  Update your MySQL credentials in grocery_app.py:

    connection = mysql.connector.connect(
    host="localhost",
    user="your_username",
    password="your_password",
    database="grocery_db"
    )

5. Run the script:

   python grocery_app.py




🧪 Sample Usage
- Add items like Rice, Milk, Eggs
- Set reorder_threshold to trigger alerts when quantity drops
- View, update, or delete items via terminal prompts or script logic



 📬 Contact
Built by Nikhil Avabarath
For backend automation, database-driven tools, and hackathon submissions.

---

Let me know if you want to add sample input/output, error handling notes, or future enhancements like CSV import or email alerts. I can help modularize the script next if you're planning to scale it.
