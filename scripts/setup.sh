#!/bin/bash
set -e
echo "Installing dependencies..."
npm install
echo "Copying config files..."
cp config/.gitignore .gitignore
cp config/.eslintrc.json .eslintrc.json
cp config/.prettierrc .prettierrc
if [ ! -f .env.local ]; then
  echo "# Add your secrets here — NEVER commit this file" > .env.local
  echo "DATABASE_URL=" >> .env.local
  echo "NEXTAUTH_SECRET=" >> .env.local
  echo "NEXTAUTH_URL=http://localhost:3000" >> .env.local
  echo "Created .env.local — fill in your values"
fi
echo "Done! Run 'npm run dev' to start."
