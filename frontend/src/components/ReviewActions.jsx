import React, { useState } from 'react';
import { reviewChange } from '../api/client';

export default function ReviewActions({ change, onRefresh }) {
  const [reviewerName, setReviewerName] = useState('');
  const [reviewNotes, setReviewNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState(null);

  async function handleReview(status) {
    if (!reviewerName.trim()) {
      setFeedback({ type: 'error', message: 'Please enter your name.' });
      return;
    }

    setLoading(true);
    setFeedback(null);

    try {
      await reviewChange(change.id, {
        status,
        reviewed_by: reviewerName.trim(),
        review_notes: reviewNotes.trim() || undefined,
      });

      setFeedback({
        type: 'success',
        message: `Change ${status} successfully.`,
      });
      setReviewNotes('');

      if (onRefresh) {
        setTimeout(() => onRefresh(), 500);
      }
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        'Failed to submit review.';
      setFeedback({ type: 'error', message: msg });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="review-actions">
      <div className="review-field">
        <label htmlFor="reviewer-name">Reviewer Name</label>
        <input
          id="reviewer-name"
          type="text"
          className="input"
          placeholder="Enter your name"
          value={reviewerName}
          onChange={(e) => setReviewerName(e.target.value)}
          disabled={loading}
        />
      </div>

      <div className="review-field">
        <label htmlFor="review-notes">Notes (optional)</label>
        <textarea
          id="review-notes"
          className="input textarea"
          placeholder="Add review notes..."
          value={reviewNotes}
          onChange={(e) => setReviewNotes(e.target.value)}
          rows={3}
          disabled={loading}
        />
      </div>

      <div className="review-btn-group">
        <button
          className="btn btn-approve"
          onClick={() => handleReview('approved')}
          disabled={loading}
        >
          {loading ? 'Submitting...' : 'Approve Change'}
        </button>
        <button
          className="btn btn-reject"
          onClick={() => handleReview('rejected')}
          disabled={loading}
        >
          {loading ? 'Submitting...' : 'Reject Change'}
        </button>
      </div>

      {feedback && (
        <div className={`feedback feedback-${feedback.type}`}>
          {feedback.message}
        </div>
      )}
    </div>
  );
}
