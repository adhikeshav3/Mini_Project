# Intelligent Student Grievance Resolution Agent Using Natural Language Processing and Machine Learning

An enterprise-grade, institutional student grievance redressal portal powered by genuine local Machine Learning (Scikit-Learn) and Natural Language Processing (NLP). 

This application operates **100% locally** without external AI APIs (no OpenAI, Gemini, or paid services required), enforcing transparent, auditable grievance resolution workflows across **Students**, **Department Staff**, and **Administrators**.

---

## 1. Project Overview

Academic institutions receive hundreds of multi-disciplinary student complaints regarding infrastructure failures, hostel hygiene, examination disputes, fee delays, and transport scheduling. Traditional mechanisms rely on manual sorting or cluttered email chains, leading to delays, misplaced complaints, and lack of transparency.

This project delivers an **Intelligent Student Grievance Resolution Agent** that parses raw student complaint narratives using NLP, automatically classifies them into institutional categories using **Logistic Regression**, predicts urgency using a **Linear Support Vector Machine (Linear SVM)** with safety escalation, classifies sentiment tone, detects semantic duplicates via **TF-IDF Cosine Similarity**, and intelligently dispatches complaints to responsible departments and available staff based on **real-time workload balancing**.

---

## 2. Key Features

- **One Integrated Web Portal**: Unified institutional portal with role-based access control (Student, Staff, Administrator) determined strictly from the database.
- **Genuine Machine Learning**:
  - **Category Classification**: TF-IDF (1-2 n-grams) + Logistic Regression across 8 institutional departments.
  - **Priority Prediction**: TF-IDF + Linear SVM (Calibrated) predicting `Low`, `Medium`, and `High` urgency.
  - **Emergency Hazard Escalation**: Deterministic safety net that scans for physical hazard keywords (fire, sparks, electrical shock, leaks) and automatically escalates urgency to `High`.
  - **Sentiment Analysis**: TF-IDF + Logistic Regression analyzing student emotional tone (`Negative`, `Neutral`, `Positive`).
  - **Duplicate Detection**: TF-IDF vectorization with Cosine Similarity matching open complaints (flagged for admin review without silent auto-merges).
  - **Intelligent Routing & Workload Balancing**: Dispatches grievances to responsible departments and assigns the staff officer with the lowest active workload.
- **Real-Time Interactive Assistant**: Live prediction preview as students draft grievances in the browser.
- **Interactive Visual Tracking**: 4-stage visual timeline (`Submitted` → `Assigned` → `In Progress` → `Resolved`) with immutable timestamped audit history.
- **Student Resolution Feedback**: 5-star rating and satisfaction comments upon grievance resolution.
- **Dynamic Administrator Analytics**: Real-time Chart.js dashboards directly mapped to live SQLite database records (Categories, Department volume, Priorities, Monthly inflow, Resolution SLA).

---

## 3. Complete Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | HTML5, CSS3, JavaScript, Bootstrap 5, Bootstrap Icons, Chart.js 4.4 |
| **Backend Framework** | Python 3.11, Flask, Flask-Login, Werkzeug |
| **Database ORM** | SQLite, SQLAlchemy 2.0 (with Scoped Sessions) |
| **NLP & Machine Learning** | Scikit-learn, TF-IDF Vectorizer, Logistic Regression, Linear SVM (LinearSVC), Cosine Similarity, Joblib, Pandas, NumPy |
| **Testing** | Python `unittest` suite (12 automated unit & integration tests) |

---

## 4. System Architecture

```text
                                WEBSITE HOMEPAGE (/)
                                         |
                                   LOGIN (/login)
                                         |
                            AUTHENTICATION (Flask-Login)
                                         |
                     -----------------------------------------
                     |                       |               |
              STUDENT ROLE              STAFF ROLE       ADMIN ROLE
                     |                       |               |
              Student Dashboard       Staff Dashboard  Admin Dashboard
                     |                       |               |
                     -----------------------------------------
                                         |
                                   FLASK BACKEND
                                         |
            -----------------------------------------------------------
            |                                                         |
     AI / ML PIPELINE                                         SQLITE DATABASE
  - NLP Text Preprocessing                                  - users
  - TF-IDF Vectorization                                    - departments
  - Category Classifier (Logistic Reg)                      - grievances
  - Priority Predictor (Linear SVM)                         - grievance_status_history
  - Sentiment Classifier (Logistic Reg)                     - duplicate_matches
  - Safety Escalation Filter                                - feedback
  - Semantic Duplicate Matching (Cosine Sim)
  - Workload Routing Engine
```

---

## 5. AI/ML Processing Pipeline

```text
       STUDENT SUBMITS GRIEVANCE (Title + Description)
                           |
                           v
               NLP TEXT PREPROCESSING
           - Lowercase conversion
           - URL / Email removal
           - Punctuation & digit stripping
           - English stopword filtering
                           |
                           v
               TF-IDF FEATURE EXTRACTION
               (Sublinear TF, 1-2 n-grams)
                           |
          -----------------------------------
          |                |                |
          v                v                v
    CATEGORY MODEL   PRIORITY MODEL  SENTIMENT MODEL
   (Logistic Reg)     (Linear SVM)    (Logistic Reg)
          |                |                |
          |                v                |
          |       SAFETY ESCALATION         |
          |       (Rule-based hazard net)   |
          |                |                |
          -----------------------------------
                           |
                           v
             SEMANTIC DUPLICATE DETECTION
         (Cosine Similarity against open cases)
                           |
                           v
             INTELLIGENT DEPARTMENT ROUTING
         (Category mapping + Staff workload check)
                           |
                           v
              PERSISTENCE & ATOMIC COMMIT
               (grievances + history table)
                           |
                           v
            DEPARTMENT OFFICER WORKSPACE
                           |
                           v
             STUDENT STATUS & FEEDBACK LOOP
```

---

## 6. Pre-Configured Demo Credentials

For quick evaluation during college project demonstrations:

| Role | Institutional Email | Password | Department / Description |
|---|---|---|---|
| **Student** | `student@college.edu` | `student123` | Rahul Sharma (Student) |
| **Student 2** | `priya@college.edu` | `student123` | Priya Patel (Student) |
| **Staff (Maintenance)** | `maintenance@college.edu` | `staff123` | Er. Rajesh Kumar (Maintenance Dept) |
| **Staff (Hostel)** | `hostel@college.edu` | `staff123` | Smt. Sunita Rao (Hostel Admin) |
| **Staff (Academic)** | `academic@college.edu` | `staff123` | Dr. Arvind Sharma (Academic Office) |
| **Staff (Exam)** | `exam@college.edu` | `staff123` | Prof. Meenakshi Sundaram (Exam Cell) |
| **Administrator** | `admin@college.edu` | `admin123` | Dean of Student Affairs |

*New students can also register via the `/register` page.*

---

## 7. Installation and Local Execution

### Step 1: Clone / Open Project in VS Code
Open the project directory in VS Code or your terminal:
```bash
cd New_Project
```

### Step 2: Create and Activate Virtual Environment
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Required Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Generate Dataset & Train ML Models
```bash
# Generate realistic training dataset
python ml/generate_dataset.py

# Train Category, Priority, and Sentiment models
python ml/train_models.py
```

### Step 5: Start Flask Application
```bash
python app.py
```

Open your browser and navigate to:
**`http://127.0.0.1:5000`**

---

## 8. Verification & Automated Test Suite

The project includes an end-to-end automated test suite covering authentication, role-based protection, inference pipelines, and lifecycle transitions:

Run the entire test suite:
```bash
python -m unittest discover tests
```

### Verified Scenarios:
1. **Scenario 1**: Student submits a grievance; verified atomic write into SQLite database.
2. **Scenario 2**: AI predicts category, priority, and sentiment via serialized `.pkl` models.
3. **Scenario 3**: Grievance routes to the correct department and assigns an available officer.
4. **Scenario 4**: Staff updates status with audit remarks; verified student timeline update.
5. **Scenario 5**: Admin analytics endpoint delivers dynamically aggregated metrics from SQLite.
6. **Scenario 6**: Unauthorized student access to administrator dashboard is blocked with 403 / redirect.

---

## 9. Viva Voce & Technical FAQ

### Q1: Why use TF-IDF instead of simple keyword matching?
*Answer*: Keyword matching is fragile because student complaints use varied vocabulary, synonyms, and phrasing. TF-IDF (Term Frequency-Inverse Document Frequency) measures how informative a word or bigram is across the entire corpus. Combined with regularized Logistic Regression and Linear SVM, it recognizes patterns even when unexpected words appear.

### Q2: Why use Linear SVM for Priority and Logistic Regression for Category?
*Answer*:
- **Logistic Regression** provides well-calibrated posterior probabilities (`predict_proba`), making it suitable for multi-class category prediction with confidence scoring.
- **Linear Support Vector Machine (LinearSVC)** maximizes the margin between decision boundaries in high-dimensional text feature spaces, making it effective for separating nuanced priority levels (`High`, `Medium`, `Low`).

### Q3: Why is there a separate Safety Escalation mechanism?
*Answer*: Machine Learning classifiers are probabilistic. Relying solely on ML for life-safety incidents (such as electrical sparks, gas leaks, structural collapse, or fire hazards) carries a risk of false negatives. The deterministic safety net guarantees that any verified hazardous condition is escalated to `High Priority` immediately.

### Q4: How does Duplicate Grievance Detection work?
*Answer*: When a complaint is submitted, its cleaned description is projected into the learned TF-IDF vector space alongside all existing active grievances. The dot product of normalized vectors computes the **Cosine Similarity**:
$$\text{Cosine Similarity}(A, B) = \frac{A \cdot B}{\|A\| \|B\|}$$
Pairs scoring $\ge 0.55$ are flagged for administrative confirmation without silent auto-merges.

### Q5: How is staff workload balanced?
*Answer*: When a grievance is routed to a department, the system queries the active workload count (`Assigned` or `In Progress`) for each staff member in that department. The grievance is assigned to the officer with the least active backlog.

---

## 10. Limitations and Future Improvements

1. **Synthetic Training Baseline**: The models are trained on realistic synthetic educational complaints. While pipeline validity is verified, institutional deployment would benefit from continuous fine-tuning on real student submissions.
2. **Multi-lingual Support**: Current NLP preprocessing is configured for English. Future enhancements can incorporate multilingual embeddings for regional languages.
3. **Email / SMS Gateway**: Can be extended with SMTP alerts to send push notifications to students upon status updates.
