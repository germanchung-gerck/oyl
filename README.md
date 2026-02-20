# Project Overview
The OYL project is designed to provide a seamless experience for users to manage their tasks efficiently. It aims to foster productivity through intuitive design and robust functionality.

# Architecture
The architecture of OYL is based on a microservices pattern, ensuring that different functionalities are encapsulated within services that communicate over defined protocols. This enhances scalability and maintainability.

# Setup Instructions
1. **Clone the Repository**  
   `git clone https://github.com/germanchung-gerck/oyl`  

2. **Install Dependencies**  
   Navigate to the project directory and run:  
   `npm install`  

3. **Start the Application**  
   Use the command:  
   `npm start`

# Tech Stack
- **Frontend:** React.js  
- **Backend:** Node.js with Express  
- **Database:** MongoDB  
- **Testing:** Jest and Enzyme  

# Folder Structure
```bash
oyl/  
├── client/          # Frontend code  
├── server/          # Backend code  
├── tests/           # Test cases  
└── README.md        # Project documentation
```  

# API Endpoints
- **GET /api/tasks** - Fetch all tasks  
- **POST /api/tasks** - Create a new task  
- **PUT /api/tasks/:id** - Update a task by ID  
- **DELETE /api/tasks/:id** - Delete a task by ID  

# Development Workflow
1. **Create a Branch**  
   Use the naming convention: `feature/{feature-name}` or `bugfix/{bug-name}`.  
2. **Make Changes**  
   Implement your changes and test locally.  
3. **Push to Remote**  
   Push your changes to GitHub.  
4. **Open a Pull Request**  
   Ensure to reference related issues.

# Contribution Guidelines
1. **Fork the Repository**  
   Create your own copy of the project.  
2. **Create a Feature Branch**  
   Work on your changes in a separate branch.  
3. **Submit your Changes**  
   Create a pull request for review, and ensure your code adheres to project standards.