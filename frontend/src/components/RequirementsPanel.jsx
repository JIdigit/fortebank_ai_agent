import React, { useState } from 'react';
import { FileText, Download, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

const RequirementsPanel = ({ sessionId, onClose }) => {
    const [projectName, setProjectName] = useState('');
    const [isGenerating, setIsGenerating] = useState(false);
    const [requirements, setRequirements] = useState(null);
    const [documentContent, setDocumentContent] = useState(null);
    const [error, setError] = useState(null);
    const [activeTab, setActiveTab] = useState('requirements');
    const [artifacts, setArtifacts] = useState({
        useCases: null,
        userStories: null,
        processDiagram: null
    });

    const generateRequirements = async () => {
        if (!projectName.trim()) {
            setError('Пожалуйста, введите название проекта');
            return;
        }

        setIsGenerating(true);
        setError(null);

        try {
            const response = await fetch('http://localhost:8000/generate-requirements', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: sessionId,
                    project_name: projectName,
                    additional_context: null
                }),
            });

            const data = await response.json();

            if (data.success) {
                setRequirements(data.requirements);
                setDocumentContent(data.document);
            } else {
                setError(data.error || 'Ошибка генерации требований');
            }
        } catch (err) {
            setError('Ошибка подключения к серверу');
            console.error(err);
        } finally {
            setIsGenerating(false);
        }
    };

    const generateArtifact = async (artifactType) => {
        if (!requirements) {
            setError('Сначала сгенерируйте требования');
            return;
        }

        setIsGenerating(true);
        setError(null);

        try {
            const response = await fetch('http://localhost:8000/generate-artifacts', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    requirements: requirements,
                    artifact_type: artifactType
                }),
            });

            const data = await response.json();

            if (data.success) {
                if (artifactType === 'use_cases') {
                    setArtifacts(prev => ({ ...prev, useCases: data.artifacts }));
                } else if (artifactType === 'user_stories') {
                    setArtifacts(prev => ({ ...prev, userStories: data.artifacts }));
                } else if (artifactType === 'process_diagram') {
                    setArtifacts(prev => ({ ...prev, processDiagram: data.diagram }));
                }
            } else {
                setError(data.error || 'Ошибка генерации артефакта');
            }
        } catch (err) {
            setError('Ошибка подключения к серверу');
            console.error(err);
        } finally {
            setIsGenerating(false);
        }
    };

    const downloadDocument = () => {
        if (!documentContent) return;

        const blob = new Blob([documentContent], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${projectName || 'requirements'}.md`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    };

    const publishToConfluence = async () => {
        if (!documentContent) {
            setError('Сначала сгенерируйте документ');
            return;
        }

        setIsGenerating(true);
        setError(null);

        try {
            console.log('📤 Publishing to Confluence...', {
                project_name: projectName,
                document_length: documentContent.length
            });

            const response = await fetch('http://localhost:8000/publish-to-confluence', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    project_name: projectName,
                    document: documentContent
                }),
            });

            const data = await response.json();
            console.log('📥 Confluence response:', data);

            if (data.success) {
                // Показываем успешное сообщение с ссылкой
                const message = `Документ успешно опубликован в Confluence!\n\nСсылка: ${data.page_url}\n\nОткрыть страницу?`;
                if (window.confirm(message)) {
                    window.open(data.page_url, '_blank');
                }
            } else {
                console.error('❌ Confluence error:', data.error);
                setError(data.error || 'Ошибка публикации в Confluence');
            }
        } catch (err) {
            console.error('❌ Exception:', err);
            setError(`Ошибка подключения к серверу: ${err.message}`);
        } finally {
            setIsGenerating(false);
        }
    };

    return (
        <div className="requirements-panel">
            <div className="panel-header">
                <h2>
                    <FileText size={24} />
                    Генератор документов
                </h2>
                <button onClick={onClose} className="close-button">×</button>
            </div>

            <div className="panel-content">
                {!requirements ? (
                    <div className="generate-section">
                        <h3>Создать документ бизнес-требований</h3>
                        <p className="text-secondary">
                            На основе вашего диалога с агентом будет создан структурированный документ требований.
                        </p>

                        <div className="form-group">
                            <label htmlFor="projectName">Название проекта</label>
                            <input
                                id="projectName"
                                type="text"
                                value={projectName}
                                onChange={(e) => setProjectName(e.target.value)}
                                placeholder="Например: Автоматизация процесса кредитования"
                                className="input-field"
                                disabled={isGenerating}
                            />
                        </div>

                        {error && (
                            <div className="error-message">
                                <AlertCircle size={16} />
                                {error}
                            </div>
                        )}

                        <button
                            onClick={generateRequirements}
                            disabled={isGenerating || !projectName.trim()}
                            className="primary-button"
                        >
                            {isGenerating ? (
                                <>
                                    <Loader2 className="animate-spin" size={16} />
                                    Генерация...
                                </>
                            ) : (
                                <>
                                    <FileText size={16} />
                                    Сгенерировать требования
                                </>
                            )}
                        </button>
                    </div>
                ) : (
                    <div className="results-section">
                        <div className="success-message">
                            <CheckCircle size={20} />
                            Документ успешно сгенерирован!
                        </div>

                        <div className="tabs">
                            <button
                                className={activeTab === 'requirements' ? 'tab active' : 'tab'}
                                onClick={() => setActiveTab('requirements')}
                            >
                                Требования
                            </button>
                            <button
                                className={activeTab === 'usecases' ? 'tab active' : 'tab'}
                                onClick={() => setActiveTab('usecases')}
                            >
                                Use Cases
                            </button>
                            <button
                                className={activeTab === 'stories' ? 'tab active' : 'tab'}
                                onClick={() => setActiveTab('stories')}
                            >
                                User Stories
                            </button>
                            <button
                                className={activeTab === 'diagram' ? 'tab active' : 'tab'}
                                onClick={() => setActiveTab('diagram')}
                            >
                                Диаграмма
                            </button>
                        </div>

                        <div className="tab-content">
                            {activeTab === 'requirements' && (
                                <div className="document-preview">
                                    <div className="markdown-content">
                                        <ReactMarkdown>{documentContent}</ReactMarkdown>
                                    </div>
                                </div>
                            )}

                            {activeTab === 'usecases' && (
                                <div>
                                    {!artifacts.useCases ? (
                                        <button
                                            onClick={() => generateArtifact('use_cases')}
                                            disabled={isGenerating}
                                            className="secondary-button"
                                        >
                                            {isGenerating ? 'Генерация...' : 'Сгенерировать Use Cases'}
                                        </button>
                                    ) : (
                                        <div className="artifacts-list">
                                            {artifacts.useCases.map((uc, idx) => (
                                                <div key={idx} className="artifact-item">
                                                    <h4>{uc.name || `Use Case ${idx + 1}`}</h4>
                                                    <p><strong>Актор:</strong> {uc.actor}</p>
                                                    <p><strong>Предусловия:</strong> {uc.preconditions}</p>
                                                    <p><strong>Основной сценарий:</strong></p>
                                                    <ol>
                                                        {uc.main_scenario?.map((step, i) => (
                                                            <li key={i}>{step}</li>
                                                        ))}
                                                    </ol>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}

                            {activeTab === 'stories' && (
                                <div>
                                    {!artifacts.userStories ? (
                                        <button
                                            onClick={() => generateArtifact('user_stories')}
                                            disabled={isGenerating}
                                            className="secondary-button"
                                        >
                                            {isGenerating ? 'Генерация...' : 'Сгенерировать User Stories'}
                                        </button>
                                    ) : (
                                        <div className="artifacts-list">
                                            {artifacts.userStories.map((story, idx) => (
                                                <div key={idx} className="artifact-item">
                                                    <p className="story-text">{story.story}</p>
                                                    <p><strong>Критерии приемки:</strong></p>
                                                    <ul>
                                                        {story.acceptance_criteria?.map((criterion, i) => (
                                                            <li key={i}>{criterion}</li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}

                            {activeTab === 'diagram' && (
                                <div>
                                    {!artifacts.processDiagram ? (
                                        <button
                                            onClick={() => generateArtifact('process_diagram')}
                                            disabled={isGenerating}
                                            className="secondary-button"
                                        >
                                            {isGenerating ? 'Генерация...' : 'Сгенерировать диаграмму'}
                                        </button>
                                    ) : (
                                        <div className="diagram-preview">
                                            <pre>{artifacts.processDiagram}</pre>
                                            <p className="text-secondary">
                                                Скопируйте код выше и вставьте в редактор Mermaid для визуализации
                                            </p>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>

                        {error && (
                            <div className="error-message">
                                <AlertCircle size={16} />
                                {error}
                            </div>
                        )}

                        <div className="action-buttons">
                            <button onClick={downloadDocument} className="secondary-button">
                                <Download size={16} />
                                Скачать документ
                            </button>
                            <button onClick={publishToConfluence} className="primary-button" disabled={isGenerating}>
                                {isGenerating ? (
                                    <>
                                        <Loader2 className="animate-spin" size={16} />
                                        Публикация...
                                    </>
                                ) : (
                                    'Опубликовать в Confluence'
                                )}
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default RequirementsPanel;
