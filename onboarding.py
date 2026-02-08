import json
import datetime

# Load role data
with open("roles.json", "r") as f:
    roles = json.load(f)

# Load existing users
with open("users.json", "r") as f:
    users = json.load(f)

# Step 1: Get employee input
name = input("Enter employee name: ").strip()
department = input("Enter department (Developer/HR/Finance/Intern): ").strip()

# Step 2: Validate department
if department not in roles:
    print("Invalid department. Please try again.")
    exit()

# Step 3: Generate username
username = name.lower().replace(" ", ".") + "." + department.lower()

# Step 4: Assign permissions
permissions = roles[department]

# Step 5: Create user record
user_data = {
    "name": name,
    "department": department,
    "permissions": permissions,
    "created_at": str(datetime.datetime.now())
}

# Step 6: Add user to database
users[username] = user_data

# Step 7: Save to users.json
with open("users.json", "w") as f:
    json.dump(users, f, indent=4)

# Step 8: Log the action
log_entry = f"{datetime.datetime.now()} - User created: {username} in {department}\n"

with open("logs.txt", "a") as log_file:
    log_file.write(log_entry)

# Step 9: Display success message
print("\nUser created successfully!")
print(f"Username: {username}")
print(f"Department: {department}")
print(f"Permissions: {permissions}")
