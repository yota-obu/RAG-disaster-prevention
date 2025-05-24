import React from 'react';
import './StockpileInputForm.css';

function StockpileInputForm({ familyMembers, onInputChange, onSubmit, isLoading }) {
  const categories = [
    { key: 'adult', label: '成人 (Adult)' },
    { key: 'child_teen', label: '子供(中学生以上) (Child - Teenager)' },
    { key: 'child_younger', label: '子供 (Child - Younger)' },
    { key: 'infant', label: '乳幼児 (Infant)' },
    { key: 'elderly', label: '高齢者 (Elderly)' },
  ];

  return (
    <form className="stockpile-input-form" onSubmit={(e) => { e.preventDefault(); onSubmit(); }}>
      {categories.map(cat => (
        <div className="form-group" key={cat.key}>
          <label htmlFor={cat.key}>{cat.label}: </label>
          <input
            type="number"
            id={cat.key}
            name={cat.key}
            value={familyMembers[cat.key]}
            onChange={(e) => onInputChange(cat.key, e.target.value)}
            min="0"
            disabled={isLoading}
          />
        </div>
      ))}
      <button type="submit" disabled={isLoading}>
        {isLoading ? '計算中...' : '計算する'}
      </button>
    </form>
  );
}

export default StockpileInputForm;
