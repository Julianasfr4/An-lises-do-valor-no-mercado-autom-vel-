#include "MlWidget.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGroupBox>
#include <QFont>
#include <QDir>
#include <QMessageBox>
#include <QFileInfo>
#include <QScrollBar>
#include <QProcessEnvironment>
#include <QDialog>  // Adicionado para criar a janela popup do gráfico
#include <QPixmap>  // Adicionado para carregar a imagem PNG

MlWidget::MlWidget(QWidget *parent)
    : QWidget(parent)
    , mlProcess(new QProcess(this))
{
    setupUi();

    connect(backButton, &QPushButton::clicked, this, &MlWidget::backToMainMenuRequested);
    connect(runTrainingButton, &QPushButton::clicked, this, &MlWidget::onRunTrainingClicked);
    connect(showGraphsButton, &QPushButton::clicked, this, &MlWidget::onShowGraphsClicked); // Reativado

    connect(sendButton, &QPushButton::clicked, this, &MlWidget::sendUserInput);
    connect(inputLineEdit, &QLineEdit::returnPressed, this, &MlWidget::sendUserInput);

    connect(mlProcess, &QProcess::readyReadStandardOutput, this, &MlWidget::readTrainingOutput);
    connect(mlProcess, &QProcess::readyReadStandardError, this, &MlWidget::readTrainingOutput);
    connect(mlProcess, QOverload<int, QProcess::ExitStatus>::of(&QProcess::finished), this, &MlWidget::onTrainingFinished);
}

MlWidget::~MlWidget() {}

void MlWidget::setupUi()
{
    QVBoxLayout *mainLayout = new QVBoxLayout(this);

    // Navigation Bar
    QHBoxLayout *headerLayout = new QHBoxLayout();
    backButton = new QPushButton(tr("← Back to Main Menu"), this);
    headerLayout->addWidget(backButton);
    headerLayout->addStretch();
    mainLayout->addLayout(headerLayout);

    // Status Panel
    QGroupBox *statusGroup = new QGroupBox(tr("Machine Learning Engine Status"), this);
    QVBoxLayout *statusLayout = new QVBoxLayout(statusGroup);

    statusLabel = new QLabel(tr("Status: Ready to calibrate predictive AI models."), this);
    statusLabel->setStyleSheet("font-size: 13px; font-weight: bold; color: #34495e;");
    statusLayout->addWidget(statusLabel);
    mainLayout->addWidget(statusGroup);

    // Action Buttons
    QHBoxLayout *actionsLayout = new QHBoxLayout();
    runTrainingButton = new QPushButton(tr("⚡ Train Predictive Models"), this);
    runTrainingButton->setStyleSheet("font-weight: bold; padding: 8px; background-color: #2da44e; color: white;");

    showGraphsButton = new QPushButton(tr("📊 View Metrics & Charts"), this);
    showGraphsButton->setStyleSheet("font-weight: bold; padding: 8px; background-color: #0366d6; color: white;");
    showGraphsButton->setEnabled(false); // Só ativa quando o treino terminar com sucesso

    actionsLayout->addWidget(runTrainingButton);
    actionsLayout->addWidget(showGraphsButton);
    mainLayout->addLayout(actionsLayout);

    // Console Output Panel
    QGroupBox *consoleGroup = new QGroupBox(tr("Live Execution Console Output"), this);
    QVBoxLayout *consoleLayout = new QVBoxLayout(consoleGroup);

    consoleLog = new QPlainTextEdit(this);
    consoleLog->setReadOnly(true);
    QFont monoFont("Courier New", 10);
    consoleLog->setFont(monoFont);
    consoleLog->setStyleSheet("background-color: #2b2b2b; color: #f0f0f0;");
    consoleLayout->addWidget(consoleLog, 1);

    // Terminal Input Layout
    QHBoxLayout *inputLayout = new QHBoxLayout();
    inputLayout->addWidget(new QLabel(tr("Terminal Input:"), this));

    inputLineEdit = new QLineEdit(this);
    inputLineEdit->setEnabled(false);
    inputLineEdit->setPlaceholderText(tr("Start the process to interact..."));

    sendButton = new QPushButton(tr("Send"), this);
    sendButton->setEnabled(false);

    inputLayout->addWidget(inputLineEdit, 1);
    inputLayout->addWidget(sendButton);
    consoleLayout->addLayout(inputLayout);

    mainLayout->addWidget(consoleGroup);
}

void MlWidget::onRunTrainingClicked()
{
    QString csvDataPath = QDir(PROJECT_SOURCE_DIR).absoluteFilePath("../JuOLXana/olx_carros.csv");

    if (!QFile::exists(csvDataPath)) {
        QString errorMsg = tr("Data file not found!\n\n"
                              "Expected location: %1\n\n"
                              "Please run the Web Scraper first to generate data.").arg(csvDataPath);
        QMessageBox::critical(this, tr("Data Missing"), errorMsg);
        consoleLog->appendPlainText(tr("[ERROR]: %1").arg(errorMsg));
        return;
    }

    QFileInfo fileInfo(csvDataPath);
    if (fileInfo.size() == 0) {
        QMessageBox::critical(this, tr("Empty Data"),
                              tr("The CSV file exists but is empty. Please run the scraper again."));
        return;
    }

    runTrainingButton->setEnabled(false);
    showGraphsButton->setEnabled(false);

    inputLineEdit->setEnabled(true);
    inputLineEdit->setPlaceholderText(tr("Type option (1-4) and press Enter..."));
    sendButton->setEnabled(true);
    inputLineEdit->setFocus();

    statusLabel->setText(tr("Status: Executing Python Training Pipeline (Pandas, Scikit-Learn)..."));
    consoleLog->clear();
    consoleLog->appendPlainText(tr(">>> Fetching scripts and launching training environment..."));
    consoleLog->appendPlainText(tr(">>> Data file: %1").arg(csvDataPath));
    consoleLog->appendPlainText(tr(">>> File size: %1 bytes").arg(fileInfo.size()));

    QString scriptPath;
#ifdef PROJECT_SOURCE_DIR
    scriptPath = QDir(PROJECT_SOURCE_DIR).absoluteFilePath("ml-training.py");
#else
    scriptPath = QDir::current().absoluteFilePath("ml-training.py");
#endif

    if (!QFile::exists(scriptPath)) {
        statusLabel->setText(tr("Status: ERROR - Training script not found!"));
        consoleLog->appendPlainText(tr("[ERROR]: Script not found at: %1").arg(scriptPath));
        runTrainingButton->setEnabled(true);
        inputLineEdit->setEnabled(false);
        sendButton->setEnabled(false);
        return;
    }

    QStringList arguments;
    arguments << "-u" << scriptPath << csvDataPath;

    mlProcess->setWorkingDirectory(QDir::currentPath());

    QProcessEnvironment env = QProcessEnvironment::systemEnvironment();
    env.insert("PYTHONIOENCODING", "utf-8");
    mlProcess->setProcessEnvironment(env);

#ifdef Q_OS_WIN
    mlProcess->start("python", arguments);
#else
    mlProcess->start("python3", arguments);
#endif

    if (!mlProcess->waitForStarted(3000)) {
        statusLabel->setText(tr("Status: CRITICAL ERROR - Failed to start Python interpreter."));
        runTrainingButton->setEnabled(true);
        inputLineEdit->setEnabled(false);
        sendButton->setEnabled(false);
        consoleLog->appendPlainText(tr("[ERROR]: 'python' execution failed. Check system environment PATH."));
        QMessageBox::critical(this, tr("Python Error"),
                              tr("Could not start Python. Make sure Python is installed and in your PATH."));
    }
}

void MlWidget::sendUserInput()
{
    QString userInput = inputLineEdit->text().trimmed();
    if (userInput.isEmpty()) return;

    if (mlProcess->state() == QProcess::Running) {
        mlProcess->write((userInput + "\n").toUtf8());
        mlProcess->waitForBytesWritten(500);

        consoleLog->appendPlainText("\n[Input Enviado: " + userInput + "]\n");
        inputLineEdit->clear();
    }
}


void MlWidget::readTrainingOutput()
{
    // Captura a saída padrão (stdout) garantindo a decodificação estrita em UTF-8
    QByteArray stdOutput = mlProcess->readAllStandardOutput();
    if (!stdOutput.isEmpty()) {
        // CORREÇÃO: Força o decoder UTF-8 puro sem misturar com o Local8Bit
        QString outputStr = QString::fromUtf8(stdOutput);

        consoleLog->appendPlainText(outputStr);
        consoleLog->verticalScrollBar()->setValue(consoleLog->verticalScrollBar()->maximum());

        if (outputStr.contains("Op", Qt::CaseInsensitive) || outputStr.contains(":")) {
            inputLineEdit->setFocus();
        }
    }

    // Captura a saída de erros (stderr) também de forma estrita em UTF-8
    QByteArray stdError = mlProcess->readAllStandardError();
    if (!stdError.isEmpty()) {
        QString errorStr = QString::fromUtf8(stdError);

        if (errorStr.contains("warning", Qt::CaseInsensitive) ||
            errorStr.contains("deprecated", Qt::CaseInsensitive)) {
            consoleLog->appendPlainText(QString("[Python Warning]: %1").arg(errorStr));
        } else {
            consoleLog->appendPlainText(QString("[Python Error]: %1").arg(errorStr));
        }
        consoleLog->verticalScrollBar()->setValue(consoleLog->verticalScrollBar()->maximum());
    }
}

void MlWidget::onTrainingFinished(int exitCode, QProcess::ExitStatus exitStatus)
{
    runTrainingButton->setEnabled(true);
    inputLineEdit->setEnabled(false);
    inputLineEdit->setPlaceholderText(tr("Start the process to interact..."));
    sendButton->setEnabled(false);

    if (exitStatus == QProcess::CrashExit) {
        statusLabel->setText(tr("Status: Process crashed! Check Python installation."));
        QMessageBox::critical(this, tr("Process Error"),
                              tr("The Python process crashed. Check if all dependencies are installed:\n"
                                 "pandas, numpy, scikit-learn, matplotlib"));
        return;
    }

    if (exitCode != 0) {
        statusLabel->setText(tr("Status: Execution failed (exit code: %1). Check console logs.").arg(exitCode));
        QMessageBox::critical(this, tr("Training Error"),
                              tr("The training script exited with errors.\n"
                                 "See console output for details."));
        return;
    }

    statusLabel->setText(tr("Status: Training successfully finished! All models are calibrated. ✅"));
    showGraphsButton->setEnabled(true); // ATIVA O BOTÃO POIS O ARQUIVO PNG JÁ EXISTE
    consoleLog->appendPlainText(tr("\n>>> Training completed successfully!"));
    consoleLog->appendPlainText(tr(">>> Models saved in: %1").arg(QDir::currentPath()));
    consoleLog->verticalScrollBar()->setValue(consoleLog->verticalScrollBar()->maximum());

    QMessageBox::information(this, tr("Training Complete"),
                             tr("Machine learning models have been trained successfully!\n"
                                "Click 'View Metrics & Charts' to view the performance plot."));
}

// CORREÇÃO: Nova implementação que abre uma janela popup dedicada e renderiza o gráfico real
void MlWidget::onShowGraphsClicked()
{
    QString graphPath = QDir::current().absoluteFilePath("comparacao_modelos.png");

    if (!QFile::exists(graphPath)) {
        QMessageBox::warning(this, tr("Plot Not Found"),
                             tr("The chart file 'comparacao_modelos.png' was not found in the working directory."));
        return;
    }

    // Cria um Dialog customizado que servirá como janela popup temporária
    QDialog *graphDialog = new QDialog(this);
    graphDialog->setWindowTitle(tr("Model Performance Analysis Chart"));
    graphDialog->setMinimumSize(800, 600); // Define um bom tamanho para ver os dados do Matplotlib

    QVBoxLayout *dialogLayout = new QVBoxLayout(graphDialog);
    QLabel *imageLabel = new QLabel(graphDialog);

    // Carrega a imagem do gráfico gerada pelo Python
    QPixmap pixmap(graphPath);

    if (pixmap.isNull()) {
        QMessageBox::critical(this, tr("Error"), tr("Failed to load the generated chart image."));
        delete graphDialog;
        return;
    }

    // Ajusta a imagem de forma proporcional para caber na janela do Qt se redimensionar
    imageLabel->setPixmap(pixmap.scaled(graphDialog->size(), Qt::KeepAspectRatio, Qt::SmoothTransformation));
    imageLabel->setAlignment(Qt::AlignCenter);

    dialogLayout->addWidget(imageLabel);
    graphDialog->setLayout(dialogLayout);

    // Exibe a janela de forma não-bloqueante (show), permitindo interagir com o resto do app
    graphDialog->setAttribute(Qt::WA_DeleteOnClose);
    graphDialog->show();

    consoleLog->appendPlainText(tr("\n>>> Opened performance analysis chart in a new window."));
    consoleLog->verticalScrollBar()->setValue(consoleLog->verticalScrollBar()->maximum());
}