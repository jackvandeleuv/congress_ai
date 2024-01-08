# Running the Django Controller and API with React Frontend

## Step 1: Clone the Repository

```cmd
git clone https://github.com/lilychen0505/capstone_web
```

## Step 2: Create 'vite.config.js' for React Frontend
Navigate to the 'react-supabase-auth' folder and create a file named 'vite.config.js'. Add the following content. Also, remember to set environment variables 'VITE_SUPABASE_URL' and 'VITE_SUPABASE_URL':
```javascript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/congressgpt': 'http://127.0.0.1:8000',
      '/api': {
        target: 'http://127.0.0.1:8000',
        rewrite: (path) => path.replace('/api', '')
      }
    }
  }
});
```
## Step 3: Install Required Python Modules
Navigate to the 'django-intro' folder and run the following command to generate 'requirements.txt'. Manually install any missing modules:

```cmd
pip freeze > requirements.txt
```
## Step 4: Run Django Controller and API
Continue in the 'django-intro' folder:
```cmd
cd django-intro
python3 manage.py migrate
python3 manage.py runserver
```
## Step 5: Run React Frontend
Open another terminal, navigate to the root folder (where 'vite.config.js' is located), and run:
```cmd
npm run dev
```
Now, your Django backend controller API and React frontend should be up and running. Ensure to replace "YOUR_SUPABASE_URL" and "YOUR_SUPABASE_KEY" with your actual Supabase project details in 'vite.config.js'.


