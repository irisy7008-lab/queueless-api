# 🎯 QueueLess API & Chatbot Integration (Prototype)

This project is a **prototype system** demonstrating how an external API can be used to power an AI-driven chatbot experience.  
It was designed to integrate with **Intercom Fin AI** (or other chat platforms) so that user queries (e.g., “Who’s hiring for a Data Analyst role?”) are processed by the API and matched with structured data such as employer names, role titles, and contact information.  

Even though the final Intercom integration was not completed due to time constraints, this repo includes the **QueueLess API** backend and clear setup instructions for extending it into a chatbot workflow.  

---

## 🚀 Project Overview
- **Backend API** built with Node.js (Express) and hosted on [Render](https://render.com).  
- **Purpose**: Search for roles and return structured JSON (company, role title, booth, contacts).  
- **Chatbot workflow (conceptual)**:  
  1. User enters a role name (e.g., “Data Analyst”).  
  2. Chatbot collects the input and calls the QueueLess API.  
  3. API returns structured data about the hiring employer.  
  4. Chatbot displays the response back to the user.  

---

## 📂 Repository Structure
```
├── api/                  # Express API source code
│   ├── routes/           # API endpoints
│   ├── data/             # Sample role data (JSON)
│   └── server.js         # Main server
├── docs/                 # Documentation and diagrams
├── README.md             # Project documentation
└── package.json          # Node.js dependencies
```

---

## ⚙️ Setup Instructions

### 1. Clone this repo
```bash
git clone https://github.com/your-username/queueless-api.git
cd queueless-api
```

### 2. Install dependencies
```bash
npm install
```

### 3. Run locally
```bash
npm start
```
The API will be available at:
```
http://localhost:3000/search
```

---

## 📡 API Usage

### Endpoint
```
POST /search
```

### Request Body
```json
{
  "role": "data analyst"
}
```

### Example Response
```json
{
  "employerName": "One NZ",
  "roleTitle": "AI Product Engineer",
  "boothCode": "A01",
  "contacts": [
    {
      "title": "Chapter Lead",
      "name": "Ethan Li",
      "linkedin": "https://www.linkedin.com/in/lc-ethan",
      "timeslot": null
    }
  ]
}
```

---

## 🧩 Chatbot Integration (Conceptual)
If integrated into **Intercom Fin AI**:  
1. **Collect customer reply** step → captures the job role.  
2. **Data Connector** → sends the role to `POST /search`.  
3. **Connector response** → maps employer + role data.  
4. **Chatbot displays structured reply** to user.  

---

## 🛡️ Known Limitations
- The Intercom Fin AI integration was **not fully connected** due to time constraints.  
- The Render free tier may **spin down** when idle (first request may be slow).  

---

## 📚 Resources
- [Render Free Hosting](https://render.com)  
- [Postman for API Testing](https://www.postman.com/)  
- [Intercom Data Connectors Guide](https://www.intercom.com/help/en/articles/9916497-how-to-set-up-data-connectors)  

---

## 📝 License
This project is licensed under the MIT License. Feel free to use and adapt.  
