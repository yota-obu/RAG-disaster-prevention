import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import StockpileSimulatorPage from './pages/StockpileSimulatorPage';
import ChatPage from './pages/ChatPage';
import './App.css'; // オプション: 基本的なスタイリング用

function App() {
  return (
    <Router>
      <div className="App">
        <Navbar />
        <div className="content">
          <Routes>
            <Route path="/" element={<StockpileSimulatorPage />} />
            <Route path="/chat" element={<ChatPage />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;
