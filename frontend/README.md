# MokaMetrics Simulator Frontend

This is the React frontend for the MokaMetrics Simulator Control Panel.

## Getting Started

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start the development server:
   ```bash
   npm run dev
   ```

3. Open your browser and navigate to `http://localhost:3000` (development) or `http://localhost:8081` (Docker)

## Authentication

The application now includes a simple login system with hard-coded credentials for demonstration purposes.

### Login Credentials

Contact your system administrator for login credentials.

### Features

- Simple login form with username and password fields
- Password visibility toggle
- Form validation and error handling
- User session management with Zustand store
- Logout functionality in the main application header

## Development

- Built with React 19, TypeScript, and Vite
- Styled with Tailwind CSS
- State management with Zustand
- UI components using Radix UI primitives

## Security Note

⚠️ **Important:** The current implementation uses hard-coded credentials for demonstration purposes only. In a production environment, you should:

1. Implement proper authentication with a backend service
2. Use secure password hashing
3. Implement JWT tokens or session management
4. Add proper authorization and role-based access control
5. Use environment variables for configuration

## Build

To build for production:

```bash
npm run build
```

The built files will be in the `dist` directory.

## Docker Deployment

The application is also available as a Docker container that includes both the frontend and backend:

1. **Build the Docker image:**
   ```bash
   cd .. # Go to MokaMetrics.Simulator directory
   make build
   ```

2. **Run the container:**
   ```bash
   make dev  # or docker compose up -d
   ```

3. **Access the application:**
   - Open `http://localhost:8081` in your browser
   - Enter your login credentials when prompted

4. **Stop the container:**
   ```bash
   make stop  # or docker compose down
   ```
