#include "TrainingWidget.h"
#include "CarSearchWidget.h"
#include "CarEvaluationWidget.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QDir>
#include <QMessageBox>
#include <QScrollBar>
#include <QProcessEnvironment>

TrainingWidget::TrainingWidget(QWidget *parent)
    : QWidget(parent), trainingProcess(new QProcess(this)), waitingForInput(false)
{
    setupUi();

    connect(runButton, &QPushButton::clicked, this, &TrainingWidget::onRunTrainingClicked);
    connect(backButton, &QPushButton::clicked, this, &TrainingWidget::backToMainMenuRequested);
    connect(sendButton, &QPushButton::clicked, this, &TrainingWidget::sendUserInput);
    connect(inputLineEdit, &QLineEdit::returnPressed, this, &TrainingWidget::sendUserInput);

    connect(trainingProcess, &QProcess::readyReadStandardOutput, this, &TrainingWidget::readProcessOutput);
    connect(trainingProcess, &QProcess::readyReadStandardError, this, &TrainingWidget::readProcessError);
    connect(trainingProcess, &QProcess::finished, this, &TrainingWidget::onProcessFinished);
}

TrainingWidget::~TrainingWidget() {}

void TrainingWidget::setupUi()
{
    QVBoxLayout *outerLayout = new QVBoxLayout(this);
    stackedWidget = new QStackedWidget(this);
    outerLayout->addWidget(stackedWidget);

    // --- TELA PRINCIPAL DO MENU DE TREINAMENTO ---
    menuContainerWidget = new QWidget(this);
    QVBoxLayout *mainLayout = new QVBoxLayout(menuContainerWidget);

    QHBoxLayout *headerLayout = new QHBoxLayout();
    backButton = new QPushButton(tr("← Back to Main Menu"), this);
    headerLayout->addWidget(backButton);
    headerLayout->addStretch();
    mainLayout->addLayout(headerLayout);

    QLabel *titleLabel = new QLabel(tr("Interactive Car Price Predictor & Machine Learning"), this);
    titleLabel->setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;");
    titleLabel->setAlignment(Qt::AlignCenter);
    mainLayout->addWidget(titleLabel);

    outputTextEdit = new QPlainTextEdit(this);
    outputTextEdit->setReadOnly(true);
    outputTextEdit->setFont(QFont("Courier New", 10));
    outputTextEdit->setStyleSheet("background-color: #2b2b2b; color: #f0f0f0;");
    mainLayout->addWidget(outputTextEdit, 1);

    QHBoxLayout *inputLayout = new QHBoxLayout();
    inputLayout->addWidget(new QLabel(tr("Terminal Input: "), this));

    inputLineEdit = new QLineEdit(this);
    inputLineEdit->setEnabled(false); // Começa desativado, ativa ao rodar o script
    inputLineEdit->setPlaceholderText(tr("Click 'Start Training Interface' to interact..."));

    sendButton = new QPushButton(tr("Send"), this);
    sendButton->setEnabled(false);

    inputLayout->addWidget(inputLineEdit, 1);
    inputLayout->addWidget(sendButton);
    mainLayout->addLayout(inputLayout);

    runButton = new QPushButton(tr("Start Training Interface"), this);
    runButton->setStyleSheet("font-weight: bold; padding: 8px; background-color: #2da44e; color: white;");
    mainLayout->addWidget(runButton);

    // --- ADICIONANDO SUB-WIDGETS NO STACKED WIDGET ---
    searchWidget = new CarSearchWidget(this);
    evaluationWidget = new CarEvaluationWidget(this);

    stackedWidget->addWidget(menuContainerWidget);  // Index 0
    stackedWidget->addWidget(searchWidget);         // Index 1
    stackedWidget->addWidget(evaluationWidget);     // Index 2

    connect(searchWidget, &CarSearchWidget::backToTrainingRequested, this, &TrainingWidget::showTrainingMenu);
    connect(evaluationWidget, &CarEvaluationWidget::backToTrainingRequested, this, &TrainingWidget::showTrainingMenu);
}

void TrainingWidget::onRunTrainingClicked()
{
    runButton->setEnabled(false);
    runButton->setText(tr("Training Interface Running..."));
    outputTextEdit->clear();

    // CORREÇÃO: O campo de texto ativa IMEDIATAMENTE ao iniciar o processo,
    // para que você possa digitar mesmo se o detector de strings falhar.
    inputLineEdit->setEnabled(true);
    inputLineEdit->setPlaceholderText(tr("Type an option (1-4) and press Enter..."));
    sendButton->setEnabled(true);
    inputLineEdit->setFocus();

    QString scriptPath = QDir(PROJECT_SOURCE_DIR).absoluteFilePath("train_car_model.py");
    QStringList arguments;
    arguments << "-u" << scriptPath; // -u remove o buffer do Python

    QProcessEnvironment env = QProcessEnvironment::systemEnvironment();
    // Força o ambiente global a usar UTF-8 no Python e no terminal do Windows
    env.insert("PYTHONIOENCODING", "utf-8");
    env.insert("PYTHONLEGACYWINDOWSSTDIO", "utf-8");
    trainingProcess->setProcessEnvironment(env);

#ifdef Q_OS_WIN
    trainingProcess->start("python", arguments);
#else
    trainingProcess->start("python3", arguments);
#endif

    if (!trainingProcess->waitForStarted(3000)) {
        QMessageBox::critical(this, tr("Error"), tr("Failed to start training script."));
        showTrainingMenu();
    }
}

void TrainingWidget::readProcessOutput()
{
    QByteArray output = trainingProcess->readAllStandardOutput();
    if (!output.isEmpty()) {
        // Tenta ler como UTF-8, se falhar devido ao Windows terminal, usa o fallback local
        QString text = QString::fromUtf8(output);
        if (text.contains("")) {
            text = QString::fromLocal8Bit(output); // Corrige os caracteres corrompidos da foto
        }

        appendOutput(text);

        // CORREÇÃO: Validação robusta de caminhos de texto para detetar a palavra "Opção" mesmo corrompida
        if (text.contains("Opção") || text.contains("Opcao") || text.contains("Op") || text.contains(":")) {
            waitingForInput = true;
            inputLineEdit->setFocus();
        }
    }
}

void TrainingWidget::readProcessError()
{
    QByteArray error = trainingProcess->readAllStandardError();
    if (!error.isEmpty()) {
        QString text = QString::fromUtf8(error);
        if (text.contains("")) text = QString::fromLocal8Bit(error);
        appendError(text);
    }
}

void TrainingWidget::sendUserInput()
{
    QString userInput = inputLineEdit->text().trimmed();
    if (userInput.isEmpty()) return;

    if (trainingProcess->state() == QProcess::Running) {
        // Envia o comando com a quebra de linha exigida pelo Python (\n)
        trainingProcess->write((userInput + "\n").toUtf8());
        trainingProcess->waitForBytesWritten(500);

        // Mostra visualmente o comando enviado no histórico do log
        appendOutput("\n[Você escolheu a opção: " + userInput + "]\n");
        inputLineEdit->clear();
        waitingForInput = false;

        // Troca de telas locais com base no comando enviado para o terminal
        if (userInput == "1") {
            searchWidget->loadDataset();
            stackedWidget->setCurrentWidget(searchWidget);
        } else if (userInput == "2") {
            stackedWidget->setCurrentWidget(evaluationWidget);
        } else if (userInput == "4") {
            appendOutput(tr("\n[A encerrar o ambiente...]\n"));
        }
    }
}

void TrainingWidget::onProcessFinished(int exitCode, QProcess::ExitStatus exitStatus)
{
    runButton->setEnabled(true);
    runButton->setText(tr("Start Training Interface"));
    inputLineEdit->setEnabled(false);
    inputLineEdit->setPlaceholderText(tr("Start the process to interact..."));
    sendButton->setEnabled(false);
    waitingForInput = false;

    if (exitStatus == QProcess::CrashExit || exitCode != 0) {
        appendError(tr("\n[Process finished with errors. Exit code: %1]").arg(exitCode));
    } else {
        appendOutput(tr("\n[Training interface closed successfully]\n"));
    }
}

void TrainingWidget::showTrainingMenu()
{
    stackedWidget->setCurrentWidget(menuContainerWidget);
    inputLineEdit->setFocus();
}

void TrainingWidget::appendOutput(const QString &text)
{
    outputTextEdit->appendPlainText(text);
    outputTextEdit->verticalScrollBar()->setValue(outputTextEdit->verticalScrollBar()->maximum());
}

void TrainingWidget::appendError(const QString &text)
{
    outputTextEdit->appendPlainText("[ERROR] " + text);
    outputTextEdit->verticalScrollBar()->setValue(outputTextEdit->verticalScrollBar()->maximum());
}