# Goody!

## Video Demo: https://youtu.be/tl_ug95L2qs

# Goody! – A Family Chore Tracker

Goody! is a web application designed to help families organize chores and rewards for kids in a clear and structured way. The application provides a simple workflow where children can submit chores they have completed and parents can review and approve them before points are awarded. By adding structure and accountability to household tasks, the app helps reinforce responsibility while also making chore tracking easier for parents.

The idea for Goody! came from a common problem in many households: chores are often tracked informally, such as through verbal agreements or whiteboards on the refrigerator. These systems frequently lead to confusion about what has been completed and whether rewards have been earned. Goody! solves this problem by creating a digital workflow where chores must be submitted and reviewed before points are granted. This ensures that both kids and parents have a shared understanding of what tasks have been completed.

This project was built as my **CS50 Final Project** using **Python, Flask, SQLite, HTML, and Bootstrap**. The application demonstrates concepts learned throughout the course, including relational database design, server-side application development, authentication, and building interactive web interfaces.

---

## How the Application Works

Goody! models a **household-based system** with two types of users: parents and kids. Every user belongs to a household, which allows multiple families to use the system independently.

Parents act as administrators of the household system. They can create chore templates, review chore submissions, and approve or reject them. Kids interact with the system by browsing available chores and submitting them when they believe they have completed the task.

The chore system uses **reusable chore templates** rather than assigning chores directly to a specific child. For example, a parent might create a template called “Clean your room” worth 10 points. When a child completes the task, they submit that chore through the application. The submission then appears in the parent dashboard where it can be reviewed and approved.

Once a chore is approved by a parent, the child is awarded the points associated with that chore template. These points can later be redeemed for rewards that parents define in the system.

---

## Rewards System

In addition to tracking chores, Goody! includes a reward redemption system. Parents can define rewards, such as “30 minutes of extra screen time” or “Choose the family movie,” and assign them a point cost. Kids can browse available rewards and request one when they have earned enough points.

However, rewards are not automatically granted. Instead, the system requires parent approval before a reward is fulfilled. This ensures that parents remain in control of how rewards are distributed and helps maintain fairness within the household.

---

## Project Structure

The application follows a typical Flask project structure. The most important files in the project include:

### app.py

`app.py` contains the main Flask application and defines all of the routes used by the system. These routes handle user authentication, dashboards for parents and kids, chore submissions, reward requests, approving or rejecting submissions, as well as helper fuctions.

This file also contains the main application logic that connects user actions from the interface with database operations.

### schema.sql

`schema.sql` defines the database schema for the application. It creates the tables used by the system, including households, users, chore templates, chore submissions, prizes, and reward requests.

Each table was designed to reflect the relationships between households, users, chores, and rewards. The schema ensures that data is properly structured and that users can only interact with data belonging to their household.

### init_db.py

`init_db.py` is a small utility script used to initialize the SQLite database. It reads the SQL commands defined in `schema.sql` and executes them to create all required tables.

This script allows the database to be quickly recreated during development or testing.

### Templates Folder

The `templates` folder contains the HTML templates used by the Flask application. These templates use **Jinja** to dynamically render content from the server.

Some key templates include:

- `layout.html`, which provides the shared layout for all pages
- `login.html` and `register.html` for user authentication
- dashboard pages for parents and kids
- forms for submitting chores and requesting rewards

Using a base layout template helps maintain consistent styling and structure across the application.

### Static Folder

The `static` folder stores the CSS file used in the html templates for standardized formatting. The project also uses **Bootstrap** to provide responsive styling and a clean user interface.

---

## Database Design

One important design decision was how to model relationships between parents, kids, and households. Instead of directly linking children to a specific parent, the application uses a **household table** that groups users together. Each user record includes a `household_id` that determines which household they belong to.

This design makes the system more flexible. It allows a household to have multiple parents and multiple children without requiring complicated relationship tables.

Another design decision involved how chores should be assigned. Initially, I considered assigning chores directly to children. However, this approach would require parents to constantly create new chore records. Instead, the final design uses **chore templates** that can be reused indefinitely. Children simply submit a template when they complete a task, which keeps the interface simple and reduces repetitive data entry.

The approval workflow was also a deliberate design choice. Rather than automatically awarding points when a child submits a chore, the system requires parent approval. This helps prevent accidental submissions or misuse and reinforces the idea that chores should be verified before rewards are granted.

---

## Future Improvements

While Goody! already provides the core functionality needed to manage chores and rewards, there are many potential improvements that could be added in the future.

Some ideas include:

- Allowing kids to upload photos as proof of chore completion
- Adding notifications for parents when chores are submitted
- Improving the mobile experience for easier use on phones
- Adding analytics for parents to track participation and progress

---

## Conclusion

Goody! demonstrates the use of Flask, relational database design, and dynamic web templates to build a practical application that solves a real-world problem. The project incorporates authentication, role-based permissions, and a multi-step workflow for chore submission and approval.

Through building this application, I gained experience designing database schemas, structuring Flask applications, and implementing features that balance simplicity with flexibility. The project reflects many of the core concepts taught in CS50 and serves as a foundation for building more complex web applications in the future.

---

## Author

Dan Herrero  
CS50 Final Project – 2026