#include "CarEvaluationWidget.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QFormLayout>
#include <QGroupBox>
#include <QDir>
#include <QMessageBox>
#include <QProcessEnvironment>

CarEvaluationWidget::CarEvaluationWidget(QWidget *parent)
    : QWidget(parent), evaluationProcess(new QProcess(this))
{
    setupUi();

    connect(evaluateButton, &QPushButton::clicked, this, &CarEvaluationWidget::onEvaluateClicked);
    connect(backButton, &QPushButton::clicked, this, &CarEvaluationWidget::backToTrainingRequested);
    connect(evaluationProcess, &QProcess::readyReadStandardOutput, this, &CarEvaluationWidget::readProcessOutput);
    connect(evaluationProcess, &QProcess::finished, this, &CarEvaluationWidget::onProcessFinished);
}

CarEvaluationWidget::~CarEvaluationWidget() {}

void CarEvaluationWidget::setupUi()
{
    QVBoxLayout *mainLayout = new QVBoxLayout(this);

    QHBoxLayout *headerLayout = new QHBoxLayout();
    backButton = new QPushButton(tr("← Back to Training Console"), this);
    headerLayout->addWidget(backButton);
    headerLayout->addStretch();
    QLabel *titleLabel = new QLabel(tr("Custom Evaluation Panel"), this);
    titleLabel->setStyleSheet("font-size: 16px; font-weight: bold;");
    headerLayout->addWidget(titleLabel);
    headerLayout->addStretch();
    mainLayout->addLayout(headerLayout);

    QGroupBox *inputGroup = new QGroupBox(tr("Target Vehicle Data"), this);
    QFormLayout *formLayout = new QFormLayout(inputGroup);

    brandInput = new QLineEdit(this);
    modelInput = new QLineEdit(this);

    yearSpinBox = new QSpinBox(this);
    yearSpinBox->setRange(1980, 2026);
    yearSpinBox->setValue(2022);

    priceSpinBox = new QSpinBox(this);
    priceSpinBox->setRange(0, 1000000);
    priceSpinBox->setSuffix(" €");

    kmSpinBox = new QSpinBox(this);
    kmSpinBox->setRange(0, 2000000);
    kmSpinBox->setSuffix(" km");

    fuelTypeCombo = new QComboBox(this);
    fuelTypeCombo->addItems({"Gasolina", "Gasóleo", "Eléctrico", "Híbrido"});

    transmissionCombo = new QComboBox(this);
    transmissionCombo->addItems({"Manual", "Automático"});

    formLayout->addRow(tr("Brand:"), brandInput);
    formLayout->addRow(tr("Model:"), modelInput);
    formLayout->addRow(tr("Year:"), yearSpinBox);
    formLayout->addRow(tr("Listed Price:"), priceSpinBox);
    formLayout->addRow(tr("Kilometers:"), kmSpinBox);
    formLayout->addRow(tr("Fuel:"), fuelTypeCombo);
    formLayout->addRow(tr("Gearbox:"), transmissionCombo);
    mainLayout->addWidget(inputGroup);

    evaluateButton = new QPushButton(tr("Execute Custom Analysis Model"), this);
    evaluateButton->setStyleSheet("font-weight: bold; padding: 10px; background-color: #2da44e; color: white;");
    mainLayout->addWidget(evaluateButton);

    QGroupBox *resultGroup = new QGroupBox(tr("Analytics Result"), this);
    QVBoxLayout *resultLayout = new QVBoxLayout(resultGroup);

    resultLabel = new QLabel(tr("Awaiting target parameters execution..."), this);
    resultLabel->setStyleSheet("font-size: 13px; font-weight: bold; padding: 8px; background-color: #f4f4f5;");
    resultLayout->addWidget(resultLabel);

    detailsTextEdit = new QPlainTextEdit(this);
    detailsTextEdit->setReadOnly(true);
    resultLayout->addWidget(detailsTextEdit);
    mainLayout->addWidget(resultGroup);
}

void CarEvaluationWidget::onEvaluateClicked()
{
    if (brandInput->text().trimmed().isEmpty() || modelInput->text().trimmed().isEmpty()) {
        QMessageBox::warning(this, tr("Warning"), tr("Please provide Brand and Model specs."));
        return;
    }

    evaluateButton->setEnabled(false);
    detailsTextEdit->clear();
    resultLabel->setText(tr("Predicting algorithmic output values..."));

    QString scriptPath = QDir(PROJECT_SOURCE_DIR).absoluteFilePath("evaluate_car.py");
    QStringList arguments;
    arguments << scriptPath;
    arguments << "--brand" << brandInput->text().trimmed();
    arguments << "--model" << modelInput->text().trimmed();
    arguments << "--year" << QString::number(yearSpinBox->value());
    arguments << "--price" << QString::number(priceSpinBox->value());
    arguments << "--km" << QString::number(kmSpinBox->value());
    arguments << "--fuel" << fuelTypeCombo->currentText();
    arguments << "--transmission" << transmissionCombo->currentText();

    QProcessEnvironment env = QProcessEnvironment::systemEnvironment();
    env.insert("PYTHONIOENCODING", "utf-8");
    evaluationProcess->setProcessEnvironment(env);

#ifdef Q_OS_WIN
    evaluationProcess->start("python", arguments);
#else
    evaluationProcess->start("python3", arguments);
#endif
}

void CarEvaluationWidget::readProcessOutput()
{
    QByteArray out = evaluationProcess->readAllStandardOutput();
    if(!out.isEmpty()) {
        QString txt = QString::fromUtf8(out);
        detailsTextEdit->appendPlainText(txt);

        if (txt.contains("Predicted value:") || txt.contains("Preço Estimado:")) {
            resultLabel->setText(txt.split('\n').first());
        }
    }
}

void CarEvaluationWidget::onProcessFinished(int exitCode, QProcess::ExitStatus exitStatus)
{
    evaluateButton->setEnabled(true);
    if(exitStatus == QProcess::CrashExit || exitCode != 0) {
        resultLabel->setText(tr("Error evaluating target system."));
    }
}