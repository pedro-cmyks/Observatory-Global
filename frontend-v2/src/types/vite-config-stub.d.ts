declare module 'vite' {
  export function defineConfig<T>(config: T): T
}

declare module '@vitejs/plugin-react' {
  export default function react(): any
}
