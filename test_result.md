# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"

#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: |
  بناء منصة GPU Cloud Pro مع:
  1. تسهيل التسجيل للمستأجرين والمزودين (تسجيل سريع، اقتراح كلمة مرور)
  2. نظام المصادقة الثنائية (2FA) بطريقتين (تطبيق + بريد)
  
backend:
  - task: "API توليد كلمة مرور"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "تم اختبار GET /api/auth/generate-password - يعمل"

  - task: "تسجيل سريع للمستخدمين"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "تم اختبار POST /api/auth/quick-register - يعمل ويولد كلمة مرور"

  - task: "تسجيل سريع للمزودين"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "تم اختبار POST /api/provider/quick-register - يعمل"

  - task: "نظام 2FA - إعداد TOTP"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "تم اختبار POST /api/auth/2fa/setup - يولد QR و manual key"

  - task: "نظام 2FA - حالة التفعيل"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "تم اختبار GET /api/auth/2fa/status - يعمل"

  - task: "تسجيل الدخول مع 2FA"
    implemented: true
    working: "NA"
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "لم يتم اختبار كامل - يحتاج تفعيل 2FA أولاً"

frontend:
  - task: "صفحة تسجيل مبسطة مع تسجيل سريع"
    implemented: true
    working: true
    file: "/app/frontend/src/App.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "تم التحقق بالـ screenshot - تظهر خيار التسجيل السريع"

  - task: "زر اقتراح كلمة مرور"
    implemented: true
    working: "NA"
    file: "/app/frontend/src/App.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "يظهر في الواجهة - يحتاج اختبار تفاعلي"

  - task: "صفحة تسجيل دخول مع دعم 2FA"
    implemented: true
    working: true
    file: "/app/frontend/src/App.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "تم التحقق بالـ screenshot - تظهر الواجهة"

  - task: "صفحة الأمان و2FA"
    implemented: true
    working: true
    file: "/app/frontend/src/App.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "تم التحقق بالـ screenshot - تظهر خيارات 2FA"

  - task: "إضافة رابط الأمان في القائمة الجانبية"
    implemented: true
    working: true
    file: "/app/frontend/src/App.js"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "يظهر في القائمة الجانبية"
