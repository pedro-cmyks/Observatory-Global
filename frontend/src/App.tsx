import { BrowserRouter as Router } from 'react-router-dom'
import GlobalObservatory from './components/GlobalObservatory/GlobalObservatory'

function App() {
  return (
    <Router>
      <GlobalObservatory />
    </Router>
  )
}

export default App

// Forced reload for Frontend Rebuild
