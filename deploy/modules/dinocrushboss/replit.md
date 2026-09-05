# Overview

This is a 3D match-3 puzzle game called "Dino Crush" built with React and Three.js. Players match dinosaur tiles on a 6x6 grid to score points and progress through 15 levels with increasing difficulty. The game features a comprehensive UI system, audio integration, progressive level mechanics, and both 3D and fallback 2D rendering options.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture

The application uses a **modern React architecture** with TypeScript and Vite as the build tool. The frontend is organized into several key layers:

- **Component Structure**: Game components are separated into screens (MainMenu, GameScreen, LevelComplete) and game-specific components (Board, DinoTile, GameUI)
- **State Management**: Uses Zustand for global state management with dedicated stores for game logic (`useDinoCrush`), general game flow (`useGame`), and audio (`useAudio`)
- **3D Rendering**: Implements React Three Fiber for 3D graphics with fallback to 2D grid-based gameplay
- **UI System**: Comprehensive component library using Radix UI primitives with Tailwind CSS for styling

## Backend Architecture

The backend follows a **minimal Express.js REST API pattern**:

- **Server Setup**: Express server with middleware for JSON parsing, logging, and error handling
- **Route Structure**: Centralized route registration in `registerRoutes` function with `/api` prefix convention
- **Storage Layer**: Abstracted storage interface (`IStorage`) with in-memory implementation (`MemStorage`) for user data
- **Development Setup**: Integrated Vite development server with HMR support

## Data Storage Solutions

- **Database**: PostgreSQL with Drizzle ORM for type-safe database operations
- **Schema Management**: Centralized schema definitions in `shared/schema.ts` using Drizzle's schema builder
- **Migration System**: Drizzle Kit for database migrations and schema synchronization
- **Development Storage**: In-memory storage implementation for rapid development and testing

## Game Logic Architecture

- **Board Generation**: Algorithm ensures no initial matches when creating new game boards
- **Match Detection**: Recursive pattern matching for horizontal and vertical combinations
- **Progressive Difficulty**: Level-specific mechanics controlling dinosaur types and power-up chances
- **Score System**: Point-based progression with configurable goals per level

## External Dependencies

- **Database**: Neon Database (PostgreSQL) via `@neondatabase/serverless`
- **3D Graphics**: React Three Fiber ecosystem (`@react-three/fiber`, `@react-three/drei`, `@react-three/postprocessing`)
- **UI Components**: Radix UI component primitives for accessible, unstyled components
- **Styling**: Tailwind CSS with custom design system integration
- **State Management**: Zustand for lightweight state management
- **Build Tools**: Vite for development and bundling, esbuild for server-side bundling
- **Form Handling**: React Hook Form with Zod validation schemas
- **Animation**: Framer Motion for UI animations and transitions
- **Audio**: Web Audio API for game sounds and background music