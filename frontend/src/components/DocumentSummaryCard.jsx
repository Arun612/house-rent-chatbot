import React from 'react';
import { FileText, DollarSign, Calendar, Clock, Info } from 'lucide-react';

export default function DocumentSummaryCard({ metadata }) {
  if (!metadata) return null;

  return (
    <div className="summary-card">
      <div className="summary-card-header">
        <FileText size={16} />
        <span>Lease Abstract</span>
      </div>
      <div className="summary-grid">
        <div className="summary-item">
          <div className="summary-item-label">
            <DollarSign size={14} /> Rent
          </div>
          <div className="summary-item-value">{metadata.rent_amount}</div>
        </div>
        <div className="summary-item">
          <div className="summary-item-label">
            <DollarSign size={14} /> Deposit
          </div>
          <div className="summary-item-value">{metadata.deposit_amount}</div>
        </div>
        <div className="summary-item">
          <div className="summary-item-label">
            <Calendar size={14} /> Term
          </div>
          <div className="summary-item-value">{metadata.lease_term}</div>
        </div>
        <div className="summary-item">
          <div className="summary-item-label">
            <Info size={14} /> Pets
          </div>
          <div className="summary-item-value">{metadata.pet_policy}</div>
        </div>
      </div>
    </div>
  );
}
