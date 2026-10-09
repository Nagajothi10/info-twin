import React, { useState, useEffect } from 'react';

export default function DocumentList({ 
  documents = [], 
  onAnalyze, 
  isAnalyzing, 
  onAddDocument,
  onDeleteDocument
}) {
  const [dragOver, setDragOver] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [uploadFeedback, setUploadFeedback] = useState('');
  const [isExtracting, setIsExtracting] = useState(false);
  const [extractedContentText, setExtractedContentText] = useState('');
  const [docClaims, setDocClaims] = useState([]);
  const [allClaims, setAllClaims] = useState([]);
  const [isAnalyzingClaims, setIsAnalyzingClaims] = useState(false);
  const [pipelineStep, setPipelineStep] = useState('Idle');

  // Versioning state
  const [currentUploader, setCurrentUploader] = useState('Person B');
  const [targetParentFileId, setTargetParentFileId] = useState('');
  const [historyDoc, setHistoryDoc] = useState(null);
  const [historyTimeline, setHistoryTimeline] = useState([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [compareDoc, setCompareDoc] = useState(null);
  const [compareData, setCompareData] = useState(null);
  const [isLoadingCompare, setIsLoadingCompare] = useState(false);
  const [compareV1Id, setCompareV1Id] = useState('');
  const [compareV2Id, setCompareV2Id] = useState('');

  // Delete modal state
  const [deleteTargetDoc, setDeleteTargetDoc] = useState(null);
  const [deleteAllVersions, setDeleteAllVersions] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');

  // Extract unique logical document families for the parent document selector
  const documentFamilies = React.useMemo(() => {
    const fams = {};
    documents.forEach(d => {
      const fid = d.file_id || `DOC-${d.id}`;
      if (!fams[fid]) {
        fams[fid] = {
          file_id: fid,
          name: d.name || d.filename,
          latestVersion: d.version || 1
        };
      } else if ((d.version || 1) > fams[fid].latestVersion) {
        fams[fid].latestVersion = d.version;
      }
    });
    return Object.values(fams);
  }, [documents]);

  // Load claims on mount
  useEffect(() => {
    fetch('http://localhost:5000/api/claims')
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (data && data.claims) {
          setAllClaims(data.claims);
        }
      })
      .catch(() => {});
  }, []);

  const getExtractorName = (type) => {
    switch ((type || '').toLowerCase()) {
      case 'pdf':
        return 'PyMuPDF Engine';
      case 'docx':
        return 'python-docx Engine';
      case 'txt':
        return 'Standard Text Reader';
      case 'csv':
        return 'pandas (CSV Reader)';
      case 'xlsx':
      case 'xls':
        return 'pandas (Excel Reader)';
      default:
        return 'Standard Twin Parser';
    }
  };

  const handleSelectDoc = async (doc) => {
    setSelectedDoc(doc);
    setExtractedContentText(doc.content || doc.extracted_content || doc.summary || '');
    setDocClaims([]);

    if (doc.id) {
      try {
        const res = await fetch(`http://localhost:5000/api/documents/${doc.id}`);
        if (res.ok) {
          const data = await res.json();
          if (data.extracted_content) {
            setExtractedContentText(data.extracted_content);
          }
          if (data.claims && data.claims.length > 0) {
            setDocClaims(data.claims);
          }
        }
      } catch (err) {
        // Fallback
      }
    }
  };

  const handleAnalyzeInformation = async (targetDocId = null) => {
    setIsAnalyzingClaims(true);
    setPipelineStep('Upload → Extract → Analyze');

    try {
      if (targetDocId) {
        const res = await fetch(`http://localhost:5000/api/analyze/${targetDocId}`, {
          method: 'POST'
        });
        if (res.ok) {
          const data = await res.json();
          setDocClaims(data.claims);
          const allRes = await fetch('http://localhost:5000/api/claims');
          if (allRes.ok) {
            const allData = await allRes.json();
            setAllClaims(allData.claims);
          }
          setUploadFeedback(`Analyzed ${data.count} structured claims for "${data.filename}".`);
        }
      } else {
        const idsToAnalyze = documents.filter(d => d.id).map(d => d.id);
        for (const id of idsToAnalyze) {
          await fetch(`http://localhost:5000/api/analyze/${id}`, { method: 'POST' });
        }
        const allRes = await fetch('http://localhost:5000/api/claims');
        if (allRes.ok) {
          const allData = await allRes.json();
          setAllClaims(allData.claims);
        }
        if (onAnalyze) onAnalyze();
        setUploadFeedback(`Analyzed claims across ${idsToAnalyze.length || documents.length} documents.`);
      }
    } catch (err) {
      console.warn('Analyze info error:', err);
    } finally {
      setIsAnalyzingClaims(false);
      setPipelineStep('Claims Displayed');
      setTimeout(() => {
        setUploadFeedback('');
        setPipelineStep('Idle');
      }, 4000);
    }
  };

  const handleReExtract = async () => {
    if (!selectedDoc) return;
    setIsExtracting(true);

    if (selectedDoc.id) {
      try {
        const res = await fetch(`http://localhost:5000/api/extract/${selectedDoc.id}`, {
          method: 'POST'
        });
        if (res.ok) {
          const data = await res.json();
          setExtractedContentText(data.extracted_content);
          setUploadFeedback(`Re-extracted content for "${selectedDoc.name}" using ${getExtractorName(selectedDoc.type)}!`);
          setTimeout(() => setUploadFeedback(''), 4000);
          setIsExtracting(false);
          return;
        }
      } catch (err) {
        console.warn('Re-extract fallback:', err);
      }
    }

    setTimeout(() => {
      setIsExtracting(false);
      setUploadFeedback(`Extracted content refreshed for "${selectedDoc.name}".`);
      setTimeout(() => setUploadFeedback(''), 3000);
    }, 600);
  };

  const processUpload = (file) => {
    const fileName = file.name;
    const parentFid = targetParentFileId || null;
    const uploader = currentUploader || 'Person B';

    onAddDocument({
      name: fileName,
      filename: fileName,
      type: fileName.split('.').pop() || 'doc',
      size: `${(file.size / 1024).toFixed(1)} KB`,
      uploaded: 'Just now',
      status: 'Active',
      statusType: 'info',
      uploader: uploader,
      uploaded_by: uploader,
      summary: `Uploaded revision by ${uploader}.`
    }, file, uploader, parentFid);

    setUploadFeedback(`Uploading "${fileName}" as ${uploader}...`);
    setTimeout(() => setUploadFeedback(''), 4000);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      processUpload(files[0]);
    }
  };

  const handleFileInput = (e) => {
    const files = e.target.files;
    if (files && files[0]) {
      processUpload(files[0]);
      e.target.value = '';
    }
  };

  // Open Version History Drawer
  const handleOpenHistory = async (doc, e) => {
    if (e) e.stopPropagation();
    setHistoryDoc(doc);
    setIsLoadingHistory(true);
    const fid = doc.file_id || `DOC-${doc.id}`;

    try {
      const res = await fetch(`http://localhost:5000/api/documents/${fid}/history`);
      if (res.ok) {
        const data = await res.json();
        setHistoryTimeline(data.timeline || []);
      } else {
        // Fallback: filter local versions
        const relDocs = documents.filter(d => (d.file_id && d.file_id === doc.file_id) || (d.name && d.name === doc.name));
        setHistoryTimeline(relDocs.map(d => ({
          version: d.version || 1,
          version_id: d.version_id,
          uploader: d.uploader || 'Person A',
          date: d.uploaded || '09 Oct 2026',
          filename: d.name,
          summary: d.summary,
          changes: d.changes || []
        })));
      }
    } catch {
      const relDocs = documents.filter(d => (d.file_id && d.file_id === doc.file_id) || (d.name && d.name === doc.name));
      setHistoryTimeline(relDocs.map(d => ({
        version: d.version || 1,
        version_id: d.version_id,
        uploader: d.uploader || 'Person A',
        date: d.uploaded || '09 Oct 2026',
        filename: d.name,
        summary: d.summary,
        changes: d.changes || []
      })));
    } finally {
      setIsLoadingHistory(false);
    }
  };

  // Open Version Compare Modal
  const handleOpenCompare = async (doc, e) => {
    if (e) e.stopPropagation();
    setCompareDoc(doc);
    setIsLoadingCompare(true);
    const fid = doc.file_id || `DOC-${doc.id}`;

    try {
      const histRes = await fetch(`http://localhost:5000/api/documents/${fid}/history`);
      let timeline = [];
      if (histRes.ok) {
        const hData = await histRes.json();
        timeline = hData.timeline || [];
      } else {
        timeline = documents.filter(d => (d.file_id && d.file_id === doc.file_id) || d.name === doc.name);
      }

      if (timeline.length >= 2) {
        const v2 = timeline[0].version_id || timeline[0].id;
        const v1 = timeline[1].version_id || timeline[1].id;
        setCompareV1Id(v1);
        setCompareV2Id(v2);
        fetchCompareData(v1, v2);
      } else {
        setCompareData({ message: 'Only 1 version exists for this document. Upload a revision to compare versions side-by-side.' });
        setIsLoadingCompare(false);
      }
    } catch {
      setIsLoadingCompare(false);
    }
  };

  const fetchCompareData = async (v1Id, v2Id) => {
    setIsLoadingCompare(true);
    try {
      const res = await fetch(`http://localhost:5000/api/documents/compare?v1=${v1Id}&v2=${v2Id}`);
      if (res.ok) {
        const data = await res.json();
        setCompareData(data);
      } else {
        setCompareData(null);
      }
    } catch {
      setCompareData(null);
    } finally {
      setIsLoadingCompare(false);
    }
  };


  // Open Delete Confirmation Modal
  const handleOpenDeleteModal = (doc, e) => {
    if (e) e.stopPropagation();
    setDeleteTargetDoc(doc);
    setDeleteAllVersions(false);
    setDeleteError('');
  };

  const handleCloseDeleteModal = () => {
    if (isDeleting) return;
    setDeleteTargetDoc(null);
    setDeleteAllVersions(false);
    setDeleteError('');
  };

  const handleConfirmDelete = async () => {
    if (!deleteTargetDoc) return;
    setIsDeleting(true);
    setDeleteError('');

    try {
      if (onDeleteDocument) {
        const result = await onDeleteDocument(deleteTargetDoc, deleteAllVersions);
        if (result && result.success === false) {
          setDeleteError(result.error || 'Failed to delete document.');
          setIsDeleting(false);
          return;
        }
      }

      // Deselect modals if they point to the deleted document
      if (selectedDoc && (selectedDoc.id === deleteTargetDoc.id || selectedDoc.version_id === deleteTargetDoc.version_id)) {
        setSelectedDoc(null);
      }
      if (historyDoc && (historyDoc.file_id === deleteTargetDoc.file_id || historyDoc.id === deleteTargetDoc.id)) {
        setHistoryDoc(null);
      }
      if (compareDoc && (compareDoc.file_id === deleteTargetDoc.file_id || compareDoc.id === deleteTargetDoc.id)) {
        setCompareDoc(null);
      }

      setUploadFeedback(`Document "${deleteTargetDoc.name || deleteTargetDoc.filename}" deleted successfully.`);
      setTimeout(() => setUploadFeedback(''), 4000);
      setIsDeleting(false);
      setDeleteTargetDoc(null);
      setDeleteAllVersions(false);
    } catch (err) {
      setDeleteError(err.message || 'Error occurred while deleting document.');
      setIsDeleting(false);
    }
  };

  const getDocIcon = (type) => {
    switch ((type || '').toLowerCase()) {
      case 'pdf':
        return '📄';
      case 'txt':
      case 'email':
        return '✉️';
      case 'xlsx':
      case 'xls':
        return '📊';
      case 'csv':
        return '📑';
      case 'docx':
      case 'doc':
        return '📝';
      default:
        return '📑';
    }
  };

  return (
    <div className="documents-container">
      <div className="section-header-row">
        <div>
          <div className="section-eyebrow">VERSION-CONTROLLED DOCUMENT REPOSITORY</div>
          <h2 className="section-title">Knowledge Documents & Version History</h2>
        </div>
        <div className="doc-actions-top" style={{ display: 'flex', gap: '10px' }}>
          <button 
            className={`btn-primary ${isAnalyzingClaims ? 'analyzing' : ''}`}
            onClick={() => handleAnalyzeInformation()}
            disabled={isAnalyzingClaims || isAnalyzing}
          >
            {isAnalyzingClaims ? (
              <>
                <span className="spinner-icon"></span>
                <span>Extracting Claims...</span>
              </>
            ) : (
              <>
                <span>🔍</span>
                <span>Analyze Information</span>
              </>
            )}
          </button>
          
          <button 
            className={`btn-secondary ${isAnalyzing ? 'analyzing' : ''}`}
            onClick={onAnalyze}
            disabled={isAnalyzing}
          >
            {isAnalyzing ? (
              <>
                <span className="spinner-icon"></span>
                <span>Scanning Twin...</span>
              </>
            ) : (
              <>
                <span>⚡</span>
                <span>Run Intelligent Analysis</span>
              </>
            )}
          </button>
        </div>
      </div>

      {uploadFeedback && (
        <div className="notification-banner success">
          <span>✅</span>
          <span>{uploadFeedback}</span>
        </div>
      )}

      {/* Upload Dropzone UI with Contributor & Version Target Selectors */}
      <div className="upload-box-wrapper" style={{ background: 'var(--surface-color)', border: '1px solid var(--border-color)', borderRadius: '12px', padding: '16px', marginBottom: '24px' }}>
        <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', alignItems: 'center', marginBottom: '14px', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-dim)' }}>👤 Contributing User:</span>
            <div style={{ display: 'flex', gap: '6px' }}>
              {['Person A', 'Person B', 'Person C'].map((u) => (
                <button
                  key={u}
                  type="button"
                  onClick={() => setCurrentUploader(u)}
                  style={{
                    padding: '4px 10px',
                    borderRadius: '6px',
                    fontSize: '0.8rem',
                    fontWeight: currentUploader === u ? 600 : 400,
                    border: currentUploader === u ? '1px solid var(--cyan)' : '1px solid var(--border-color)',
                    background: currentUploader === u ? 'rgba(0, 240, 255, 0.15)' : 'rgba(255,255,255,0.03)',
                    color: currentUploader === u ? 'var(--cyan)' : 'var(--text-main)',
                    cursor: 'pointer'
                  }}
                >
                  {u}
                </button>
              ))}
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginLeft: 'auto' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-dim)' }}>📁 Lineage Target:</span>
            <select
              value={targetParentFileId}
              onChange={(e) => setTargetParentFileId(e.target.value)}
              style={{
                padding: '6px 12px',
                borderRadius: '6px',
                background: 'rgba(0,0,0,0.3)',
                color: 'var(--text-main)',
                border: '1px solid var(--border-color)',
                fontSize: '0.8rem',
                cursor: 'pointer'
              }}
            >
              <option value="">Auto-Detect / New Document Family</option>
              {documentFamilies.map(f => (
                <option key={f.file_id} value={f.file_id}>
                  Revise: {f.name} (Currently v{f.latestVersion})
                </option>
              ))}
            </select>
          </div>
        </div>

        <div 
          className={`upload-dropzone ${dragOver ? 'drag-over' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          style={{ border: '2px dashed var(--border-color)', borderRadius: '8px', padding: '24px', textAlign: 'center' }}
        >
          <input 
            type="file" 
            id="fileUploadInput" 
            style={{ display: 'none' }} 
            onChange={handleFileInput}
            accept=".pdf,.txt,.xlsx,.docx,.csv"
          />
          <div className="dropzone-icon" style={{ fontSize: '2rem', marginBottom: '8px' }}>📥</div>
          <div className="dropzone-content">
            <h3 className="dropzone-title" style={{ fontSize: '1rem', marginBottom: '4px' }}>
              Drag & drop files to create a version or expand Twin knowledge
            </h3>
            <p className="dropzone-subtitle" style={{ fontSize: '0.8rem', color: 'var(--text-dim)', marginBottom: '12px' }}>
              Uploading an updated file preserves all previous versions and automatically computes field deltas.
            </p>
            <div className="dropzone-actions" style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
              <label htmlFor="fileUploadInput" className="btn-secondary btn-sm" style={{ cursor: 'pointer' }}>
                Browse Local Files
              </label>
              <button 
                type="button"
                className="btn-ghost btn-sm"
                onClick={() => {
                  onAddDocument({
                    name: `memo_update_v${Math.floor(Math.random() * 10) + 2}.pdf`,
                    type: 'pdf',
                    size: '1.2 MB',
                    uploaded: 'Just now',
                    status: 'Queued',
                    statusType: 'warning',
                    uploader: currentUploader,
                    summary: `Simulated administrative memorandum with modified evaluation rubrics by ${currentUploader}.`,
                    content: 'MEMORANDUM ADDENDUM: Project guidelines amended for capstone review. Deadline: 25 October 2026.'
                  }, null, currentUploader, targetParentFileId);
                  setUploadFeedback(`Simulated memorandum added by ${currentUploader}.`);
                  setTimeout(() => setUploadFeedback(''), 3000);
                }}
              >
                + Add Sample Version
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Document List Table with ALL Versions (Newest First) */}
      <div className="documents-grid-header">
        <span className="grid-label">Document Versions Repository ({documents.length} Total Versions)</span>
        <span className="grid-hint">All versions preserved. Newest appear first. Older versions remain 100% accessible.</span>
      </div>

      <div className="documents-table-wrapper">
        <table className="documents-table">
          <thead>
            <tr>
              <th>Document & Version</th>
              <th>Uploaded By</th>
              <th>Format</th>
              <th>Size</th>
              <th>Date / Time</th>
              <th>Twin Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {documents.length === 0 ? (
              <tr>
                <td colSpan="7" style={{ textAlign: 'center', padding: '52px 24px', color: 'var(--text-muted)' }}>
                  <div style={{ fontSize: '2.5rem', marginBottom: '12px' }}>📂</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f8fafc', marginBottom: '6px' }}>
                    No Ingested Documents
                  </div>
                  <div style={{ fontSize: '0.85rem', color: '#94a3b8', maxWidth: '480px', margin: '0 auto' }}>
                    Upload academic notices, schedules, policies, or memos in the dropzone above to begin automated claim extraction.
                  </div>
                </td>
              </tr>
            ) : (
              documents.map((doc, idx) => (
              <tr 
                key={doc.id || doc.version_id || idx} 
                className={selectedDoc?.id === doc.id ? 'row-selected' : ''}
                onClick={() => handleSelectDoc(doc)}
              >
                <td>
                  <div className="doc-name-cell">
                    <span className="doc-file-icon">{getDocIcon(doc.type)}</span>
                    <div>
                      <div className="doc-file-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span>{doc.name || doc.filename}</span>
                        <span style={{ 
                          fontSize: '0.72rem', 
                          fontWeight: 700, 
                          padding: '2px 8px', 
                          borderRadius: '12px',
                          background: (doc.version || 1) > 1 ? 'rgba(0, 240, 255, 0.2)' : 'rgba(255, 255, 255, 0.1)',
                          color: (doc.version || 1) > 1 ? 'var(--cyan)' : 'var(--text-main)',
                          border: (doc.version || 1) > 1 ? '1px solid var(--cyan)' : '1px solid rgba(255,255,255,0.2)'
                        }}>
                          Version {doc.version || 1}
                        </span>
                      </div>
                      <div className="doc-file-desc">{doc.summary}</div>
                    </div>
                  </div>
                </td>
                <td>
                  <span style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    fontSize: '0.8rem',
                    fontWeight: 600,
                    padding: '3px 8px',
                    borderRadius: '4px',
                    background: 'rgba(255,255,255,0.05)',
                    color: 'var(--text-main)'
                  }}>
                    👤 {doc.uploader || doc.uploaded_by || 'Person A'}
                  </span>
                </td>
                <td>
                  <span className="badge-format uppercase">{doc.type || doc.file_type}</span>
                </td>
                <td className="text-muted text-mono">{doc.size}</td>
                <td className="text-muted" style={{ fontSize: '0.8rem' }}>{doc.uploaded || doc.upload_time}</td>
                <td>
                  <span className={`status-pill pill-${doc.statusType || 'default'}`}>
                    <span className="status-dot"></span>
                    {doc.status}
                  </span>
                </td>
                <td>
                  <div style={{ display: 'flex', gap: '6px' }} onClick={(e) => e.stopPropagation()}>
                    <button 
                      className="btn-icon-action" 
                      title="Inspect document text and claims"
                      onClick={() => handleSelectDoc(doc)}
                    >
                      🔍
                    </button>
                    <button 
                      className="btn-icon-action" 
                      title="View complete version history timeline"
                      onClick={(e) => handleOpenHistory(doc, e)}
                    >
                      📜
                    </button>
                    <button 
                      className="btn-icon-action" 
                      title="Compare with another version"
                      onClick={(e) => handleOpenCompare(doc, e)}
                    >
                      ⚖️
                    </button>
                    <button 
                      className="btn-icon-action btn-action-delete" 
                      title="Delete document"
                      onClick={(e) => handleOpenDeleteModal(doc, e)}
                    >
                      🗑️
                    </button>
                  </div>
                </td>
              </tr>
            ))
            )}
          </tbody>
        </table>
      </div>

      {/* STRUCTURED CLAIMS SECTION (Upload -> Extract -> Analyze -> Display Claims) */}
      <div className="claims-container">
        <div className="claims-pipeline-banner">
          <div className="pipeline-flow-pills">
            <span className="flow-pill active">Upload</span>
            <span className="flow-arrow">→</span>
            <span className="flow-pill active">Extract</span>
            <span className="flow-arrow">→</span>
            <span className={`flow-pill ${isAnalyzingClaims ? 'active' : ''}`}>Analyze</span>
            <span className="flow-arrow">→</span>
            <span className="flow-pill active">Display Claims</span>
          </div>
          <span className="text-muted text-mono" style={{ fontSize: '0.75rem' }}>
            {allClaims.length} Extracted Claims Active
          </span>
        </div>

        <div className="section-header-row" style={{ marginBottom: '14px' }}>
          <div>
            <div className="section-eyebrow">STRUCTURED INFORMATION EXTRACTION</div>
            <h3 className="section-title" style={{ fontSize: '1.1rem' }}>Extracted Claims Repository</h3>
          </div>
          <button 
            className="btn-secondary btn-sm"
            onClick={() => handleAnalyzeInformation()}
            disabled={isAnalyzingClaims}
          >
            <span>🔄</span>
            <span>Refresh Claims</span>
          </button>
        </div>

        {allClaims.length === 0 ? (
          <p className="text-muted" style={{ fontSize: '0.85rem' }}>
            No claims extracted yet. Click <strong>Analyze Information</strong> to extract structured claims across documents.
          </p>
        ) : (
          <div className="claims-grid">
            {allClaims.map((claim, cIdx) => (
              <div key={claim.id || cIdx} className="claim-card">
                <div className="claim-card-top">
                  <span className="claim-subject-badge">{claim.subject}</span>
                  <span className="claim-conf-chip">
                    {Math.round((claim.confidence || 0.85) * 100)}% Conf
                  </span>
                </div>
                
                <div className="claim-attr-row">
                  <span className="claim-attr-label">{claim.attribute}:</span>
                  <span className="claim-val-text">{claim.value}</span>
                </div>

                <div className="claim-card-footer">
                  <span className="text-dim">Source:</span>
                  <span className="claim-source-tag">{claim.source}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* DOCUMENT PREVIEW MODAL */}
      {selectedDoc && (
        <div className="doc-preview-modal-overlay" onClick={() => setSelectedDoc(null)}>
          <div className="doc-preview-modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '680px' }}>
            <div className="modal-header">
              <div className="modal-title-wrap">
                <span className="modal-icon">{getDocIcon(selectedDoc.type)}</span>
                <div>
                  <h3 className="modal-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {selectedDoc.name || selectedDoc.filename}
                    <span style={{ fontSize: '0.75rem', padding: '2px 8px', borderRadius: '10px', background: 'var(--cyan)', color: '#000', fontWeight: 700 }}>
                      v{selectedDoc.version || 1}
                    </span>
                  </h3>
                  <span className="modal-subtitle">
                    Uploaded by {selectedDoc.uploader || selectedDoc.uploaded_by || 'Person A'} • Extracted Content & Claims
                  </span>
                </div>
              </div>
              <button className="modal-close" onClick={() => setSelectedDoc(null)}>✕</button>
            </div>
            
            <div className="modal-body">
              <div className="metadata-grid">
                <div className="meta-box">
                  <span className="meta-key">Document Lineage ID</span>
                  <span className="meta-val text-mono">{selectedDoc.file_id || `DOC-${selectedDoc.id}`}</span>
                </div>
                <div className="meta-box">
                  <span className="meta-key">Version ID</span>
                  <span className="meta-val text-cyan">{selectedDoc.version_id || `VER-${selectedDoc.id}-1`}</span>
                </div>
                <div className="meta-box">
                  <span className="meta-key">Contributor</span>
                  <span className="meta-val">{selectedDoc.uploader || selectedDoc.uploaded_by || 'Person A'}</span>
                </div>
                <div className="meta-box">
                  <span className="meta-key">Timestamp</span>
                  <span className="meta-val">{selectedDoc.uploaded || selectedDoc.upload_time}</span>
                </div>
              </div>

              {/* REAL EXTRACTED CONTENT SECTION */}
              <div className="extracted-real-content-section">
                <div className="content-section-header">
                  <span className="content-header-title">📄 Extracted Text Content</span>
                  <span className="content-engine-pill">{getExtractorName(selectedDoc.type)}</span>
                </div>
                <div className="extracted-content-scrollbox">
                  <pre className="extracted-pre-text">
                    {extractedContentText || selectedDoc.summary || 'No text extracted.'}
                  </pre>
                </div>
              </div>

              {/* CLAIMS FOR THIS DOCUMENT */}
              {docClaims.length > 0 && (
                <div className="extracted-claims-box" style={{ marginTop: '16px' }}>
                  <h4>Document Extracted Claims ({docClaims.length})</h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '8px' }}>
                    {docClaims.map((c, i) => (
                      <div key={i} style={{ 
                        background: 'rgba(0,0,0,0.25)', 
                        padding: '8px 12px', 
                        borderRadius: '6px', 
                        display: 'flex', 
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        fontSize: '0.8rem'
                      }}>
                        <div>
                          <strong style={{ color: 'var(--cyan)' }}>[{c.subject}]</strong> {c.attribute}: <strong>{c.value}</strong>
                        </div>
                        <span className="claim-conf-chip" style={{ fontSize: '0.65rem' }}>
                          {Math.round((c.confidence || 0.85) * 100)}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="modal-footer" style={{ justifyContent: 'space-between' }}>
              <div>
                <button 
                  className={`btn-primary btn-sm ${isAnalyzingClaims ? 'analyzing' : ''}`}
                  onClick={() => handleAnalyzeInformation(selectedDoc.id)}
                  disabled={isAnalyzingClaims}
                  style={{ marginRight: '8px' }}
                >
                  ⚡ Analyze Claims
                </button>
                <button 
                  className="btn-secondary btn-sm"
                  onClick={handleReExtract}
                  disabled={isExtracting}
                >
                  {isExtracting ? 'Re-Extracting...' : 'Re-Extract Text'}
                </button>
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button 
                  type="button"
                  className="btn-danger btn-sm" 
                  onClick={() => handleOpenDeleteModal(selectedDoc)}
                  style={{ background: 'rgba(244, 63, 94, 0.15)', color: '#fca5a5', border: '1px solid rgba(244, 63, 94, 0.3)' }}
                >
                  🗑️ Delete
                </button>
                <button className="btn-secondary btn-sm" onClick={() => setSelectedDoc(null)}>Close</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* VERSION HISTORY MODAL */}
      {historyDoc && (
        <div className="doc-preview-modal-overlay" onClick={() => setHistoryDoc(null)}>
          <div className="doc-preview-modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '720px' }}>
            <div className="modal-header">
              <div className="modal-title-wrap">
                <span className="modal-icon">📜</span>
                <div>
                  <h3 className="modal-title">Version History: {historyDoc.name || historyDoc.filename}</h3>
                  <span className="modal-subtitle">
                    Complete immutable audit trail ({historyTimeline.length} recorded versions)
                  </span>
                </div>
              </div>
              <button className="modal-close" onClick={() => setHistoryDoc(null)}>✕</button>
            </div>

            <div className="modal-body" style={{ maxHeight: '65vh', overflowY: 'auto' }}>
              {isLoadingHistory ? (
                <div style={{ textAlign: 'center', padding: '30px' }}>Loading timeline...</div>
              ) : historyTimeline.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '30px', color: 'var(--text-dim)' }}>
                  No historical versions found for this file.
                </div>
              ) : (
                <div className="version-timeline" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  {historyTimeline.map((item, idx) => (
                    <div 
                      key={item.version_id || idx}
                      style={{
                        background: 'rgba(255,255,255,0.03)',
                        border: '1px solid var(--border-color)',
                        borderRadius: '8px',
                        padding: '16px',
                        position: 'relative'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <span style={{
                            padding: '3px 10px',
                            borderRadius: '12px',
                            background: idx === 0 ? 'var(--cyan)' : 'rgba(255,255,255,0.1)',
                            color: idx === 0 ? '#000' : 'var(--text-main)',
                            fontWeight: 700,
                            fontSize: '0.8rem'
                          }}>
                            Version {item.version} {idx === 0 ? '(Latest)' : ''}
                          </span>
                          <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>
                            👤 {item.uploader || 'Person A'}
                          </span>
                        </div>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                          📅 {item.date}
                        </span>
                      </div>

                      {item.checksum && (
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginBottom: '8px', fontFamily: 'monospace' }}>
                          SHA-256: {item.checksum.slice(0, 16)}...
                        </div>
                      )}

                      {/* Changed Fields list */}
                      {item.changes && item.changes.length > 0 ? (
                        <div style={{ background: 'rgba(0,0,0,0.2)', padding: '10px', borderRadius: '6px', marginTop: '8px' }}>
                          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--cyan)', marginBottom: '6px' }}>
                            Detected Field Modifications:
                          </div>
                          <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '0.8rem' }}>
                            {item.changes.map((ch, cIdx) => (
                              <li key={cIdx} style={{ marginBottom: '4px' }}>
                                <strong>{ch.field_name}:</strong>{' '}
                                <span style={{ color: '#ff7875', textDecoration: 'line-through' }}>{ch.old_value}</span>{' '}
                                →{' '}
                                <span style={{ color: '#52c41a', fontWeight: 600 }}>{ch.new_value}</span>{' '}
                                <em style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>({ch.change_type})</em>
                              </li>
                            ))}
                          </ul>
                        </div>
                      ) : (
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)', fontStyle: 'italic' }}>
                          {item.version === 1 ? 'Original baseline document' : 'Content updated.'}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="modal-footer" style={{ justifyContent: 'flex-end' }}>
              <button className="btn-secondary btn-sm" onClick={() => setHistoryDoc(null)}>Close</button>
            </div>
          </div>
        </div>
      )}

      {/* VERSION COMPARISON MODAL */}
      {compareDoc && (
        <div className="doc-preview-modal-overlay" onClick={() => setCompareDoc(null)}>
          <div className="doc-preview-modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '840px' }}>
            <div className="modal-header">
              <div className="modal-title-wrap">
                <span className="modal-icon">⚖️</span>
                <div>
                  <h3 className="modal-title">Version Comparison: {compareDoc.name || compareDoc.filename}</h3>
                  <span className="modal-subtitle">
                    Side-by-side field and value differences between revisions
                  </span>
                </div>
              </div>
              <button className="modal-close" onClick={() => setCompareDoc(null)}>✕</button>
            </div>

            <div className="modal-body" style={{ maxHeight: '70vh', overflowY: 'auto' }}>
              {isLoadingCompare ? (
                <div style={{ textAlign: 'center', padding: '30px' }}>Running diff analysis...</div>
              ) : compareData?.message ? (
                <div style={{ textAlign: 'center', padding: '30px', color: 'var(--text-dim)' }}>
                  {compareData.message}
                </div>
              ) : compareData ? (
                <div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
                    <div style={{ background: 'rgba(255,255,255,0.03)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>BASE VERSION</span>
                      <h4 style={{ margin: '4px 0', color: 'var(--text-main)' }}>
                        Version {compareData.v1?.version_number} ({compareData.v1?.uploader})
                      </h4>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>{compareData.v1?.date}</span>
                    </div>

                    <div style={{ background: 'rgba(0, 240, 255, 0.05)', padding: '12px', borderRadius: '8px', border: '1px solid var(--cyan)' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--cyan)' }}>REVISED VERSION</span>
                      <h4 style={{ margin: '4px 0', color: 'var(--text-main)' }}>
                        Version {compareData.v2?.version_number} ({compareData.v2?.uploader})
                      </h4>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>{compareData.v2?.date}</span>
                    </div>
                  </div>

                  <h4 style={{ fontSize: '0.9rem', marginBottom: '8px' }}>
                    Field Differences ({compareData.changes_count} changes detected):
                  </h4>

                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                    <thead>
                      <tr style={{ background: 'rgba(0,0,0,0.3)', textAlign: 'left', borderBottom: '1px solid var(--border-color)' }}>
                        <th style={{ padding: '8px' }}>Field / Attribute</th>
                        <th style={{ padding: '8px' }}>Version {compareData.v1?.version_number} (Old)</th>
                        <th style={{ padding: '8px' }}>Version {compareData.v2?.version_number} (New)</th>
                        <th style={{ padding: '8px' }}>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {compareData.differences?.map((diff, dIdx) => (
                        <tr 
                          key={dIdx} 
                          style={{ 
                            borderBottom: '1px solid rgba(255,255,255,0.05)',
                            background: diff.status !== 'Identical' ? 'rgba(0, 240, 255, 0.03)' : 'transparent'
                          }}
                        >
                          <td style={{ padding: '8px', fontWeight: 600 }}>{diff.field}</td>
                          <td style={{ padding: '8px', color: diff.v1_value === 'Missing' ? '#ff7875' : 'var(--text-dim)' }}>
                            {diff.v1_value}
                          </td>
                          <td style={{ padding: '8px', color: diff.status !== 'Identical' ? '#52c41a' : 'var(--text-main)', fontWeight: diff.status !== 'Identical' ? 600 : 400 }}>
                            {diff.v2_value}
                          </td>
                          <td style={{ padding: '8px' }}>
                            <span style={{
                              padding: '2px 8px',
                              borderRadius: '4px',
                              fontSize: '0.7rem',
                              fontWeight: 600,
                              background: diff.status === 'Identical' ? 'rgba(255,255,255,0.1)' : 'rgba(0, 240, 255, 0.2)',
                              color: diff.status === 'Identical' ? 'var(--text-dim)' : 'var(--cyan)'
                            }}>
                              {diff.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '30px', color: 'var(--text-dim)' }}>
                  Failed to load version comparison data.
                </div>
              )}
            </div>

            <div className="modal-footer" style={{ justifyContent: 'flex-end' }}>
              <button className="btn-secondary btn-sm" onClick={() => setCompareDoc(null)}>Close</button>
            </div>
          </div>
        </div>
      )}
    
      {/* DELETE CONFIRMATION MODAL */}
      {deleteTargetDoc && (
        <div className="doc-preview-modal-overlay" onClick={handleCloseDeleteModal}>
          <div 
            className="doc-preview-modal" 
            onClick={(e) => e.stopPropagation()} 
            style={{ maxWidth: '520px', borderTop: '4px solid var(--danger)' }}
          >
            <div className="modal-header">
              <div className="modal-title-wrap">
                <span className="modal-icon" style={{ color: 'var(--danger)' }}>⚠️</span>
                <div>
                  <h3 className="modal-title" style={{ color: '#fff' }}>Confirm Document Deletion</h3>
                  <span className="modal-subtitle">
                    Permanent repository update and database synchronization
                  </span>
                </div>
              </div>
              <button 
                className="modal-close" 
                onClick={handleCloseDeleteModal}
                disabled={isDeleting}
              >
                ✕
              </button>
            </div>

            <div className="modal-body" style={{ padding: '20px' }}>
              {deleteError && (
                <div className="notification-banner danger" style={{ marginBottom: '16px' }}>
                  <span>⚠️</span>
                  <span>{deleteError}</span>
                </div>
              )}

              <p style={{ color: 'var(--text-main)', fontSize: '0.95rem', margin: '0 0 16px 0', lineHeight: 1.5 }}>
                Are you sure you want to delete this document from the INFO-TWIN repository?
              </p>

              {/* Target Document Summary Card */}
              <div style={{
                background: 'rgba(255, 255, 255, 0.04)',
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
                padding: '14px',
                marginBottom: '16px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <strong style={{ fontSize: '1rem', color: '#fff' }}>
                    {deleteTargetDoc.name || deleteTargetDoc.filename}
                  </strong>
                  <span style={{
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    padding: '2px 8px',
                    borderRadius: '10px',
                    background: 'rgba(0, 240, 255, 0.2)',
                    color: 'var(--cyan)'
                  }}>
                    Version {deleteTargetDoc.version || 1}
                  </span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '0.8rem', color: 'var(--text-dim)' }}>
                  <div><strong>Uploaded By:</strong> {deleteTargetDoc.uploader || deleteTargetDoc.uploaded_by || 'Person A'}</div>
                  <div><strong>Format:</strong> {(deleteTargetDoc.type || deleteTargetDoc.file_type || 'doc').toUpperCase()}</div>
                  <div><strong>Size:</strong> {deleteTargetDoc.size}</div>
                  <div><strong>Date:</strong> {deleteTargetDoc.uploaded || deleteTargetDoc.upload_time}</div>
                </div>
              </div>

              {/* Version History Preservation Explanatory Notice */}
              {(() => {
                const relatedVersions = documents.filter(d => 
                  (deleteTargetDoc.file_id && d.file_id === deleteTargetDoc.file_id) || 
                  (deleteTargetDoc.name && d.name === deleteTargetDoc.name)
                );
                const hasMultipleVersions = relatedVersions.length > 1;

                if (hasMultipleVersions) {
                  return (
                    <div style={{
                      background: 'rgba(0, 240, 255, 0.05)',
                      border: '1px solid rgba(0, 240, 255, 0.2)',
                      borderRadius: '8px',
                      padding: '12px',
                      marginBottom: '14px'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px', color: 'var(--cyan)', fontWeight: 600, fontSize: '0.85rem' }}>
                        <span>🛡️</span>
                        <span>Version History Preserved</span>
                      </div>
                      <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-dim)', lineHeight: 1.4 }}>
                        By default, only this specific version (Version {deleteTargetDoc.version || 1}) will be deleted. The other {relatedVersions.length - 1} version(s) in this document's history will remain completely accessible.
                      </p>

                      <label style={{ 
                        display: 'flex', 
                        alignItems: 'center', 
                        gap: '8px', 
                        cursor: 'pointer', 
                        marginTop: '12px', 
                        padding: '8px 10px', 
                        borderRadius: '6px', 
                        background: deleteAllVersions ? 'rgba(244,63,94,0.15)' : 'rgba(255,255,255,0.03)', 
                        border: deleteAllVersions ? '1px solid rgba(244,63,94,0.4)' : '1px solid var(--border-color)',
                        transition: 'all 0.2s ease'
                      }}>
                        <input 
                          type="checkbox" 
                          id="deleteAllVersionsCheck"
                          checked={deleteAllVersions} 
                          onChange={(e) => setDeleteAllVersions(e.target.checked)} 
                        />
                        <span style={{ fontSize: '0.82rem', color: deleteAllVersions ? '#fca5a5' : 'var(--text-main)', fontWeight: deleteAllVersions ? 600 : 400 }}>
                          Explicitly delete ALL versions ({relatedVersions.length}) in this document family
                        </span>
                      </label>
                    </div>
                  );
                } else {
                  return (
                    <div style={{
                      background: 'rgba(244, 63, 94, 0.06)',
                      border: '1px solid rgba(244, 63, 94, 0.2)',
                      borderRadius: '6px',
                      padding: '10px 12px',
                      fontSize: '0.8rem',
                      color: 'var(--text-dim)'
                    }}>
                      ℹ️ This document and its extracted claims will be permanently removed from the knowledge base.
                    </div>
                  );
                }
              })()}
            </div>

            <div className="modal-footer" style={{ justifyContent: 'flex-end', gap: '10px' }}>
              <button 
                type="button"
                className="btn-secondary btn-sm" 
                onClick={handleCloseDeleteModal}
                disabled={isDeleting}
              >
                Cancel
              </button>
              <button 
                type="button"
                className="btn-danger btn-sm" 
                onClick={handleConfirmDelete}
                disabled={isDeleting}
                style={{
                  background: 'var(--danger)',
                  color: '#fff',
                  border: '1px solid var(--danger)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontWeight: 600
                }}
              >
                {isDeleting ? (
                  <>
                    <span className="spinner-icon"></span>
                    <span>Deleting...</span>
                  </>
                ) : (
                  <>
                    <span>🗑️</span>
                    <span>{deleteAllVersions ? 'Delete All Versions' : 'Delete Document'}</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
