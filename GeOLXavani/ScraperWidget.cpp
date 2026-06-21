#include "ScraperWidget.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QFormLayout>
#include <QGroupBox>
#include <QHeaderView>
#include <QFile>
#include <QTextStream>
#include <QDateTime>
#include <QDir>
#include <QDebug>
#include <QMessageBox>

ScraperWidget::ScraperWidget(QWidget *parent)
    : QWidget(parent), scraperProcess(new QProcess(this))
{
    setupUi();

    connect(runButton, &QPushButton::clicked, this, &ScraperWidget::onRunScraperClicked);
    connect(backButton, &QPushButton::clicked, this, &ScraperWidget::backToMainMenuRequested);
    connect(scraperProcess, &QProcess::readyReadStandardOutput, this, &ScraperWidget::readScraperOutput);
    connect(scraperProcess, &QProcess::readyReadStandardError, this, &ScraperWidget::readScraperOutput);
    connect(scraperProcess, &QProcess::finished, this, &ScraperWidget::onScraperFinished);
}

ScraperWidget::~ScraperWidget() {}

void ScraperWidget::setupUi()
{
    QVBoxLayout *mainLayout = new QVBoxLayout(this);

    // Header navigation row
    QHBoxLayout *headerLayout = new QHBoxLayout();
    backButton = new QPushButton(tr("← Back to Main Menu"), this);
    headerLayout->addWidget(backButton);
    headerLayout->addStretch();
    mainLayout->addLayout(headerLayout);

    // Filters Configuration Panel
    QGroupBox *filterGroup = new QGroupBox(tr("OLX Portugal Webscraping Parameters"), this);
    QFormLayout *formLayout = new QFormLayout(filterGroup);

    brandInput = new QLineEdit(this);
    brandInput->setPlaceholderText(tr("e.g., BMW, Audi (Optional)"));

    pagesSpinBox = new QSpinBox(this);
    pagesSpinBox->setRange(1, 100);
    pagesSpinBox->setValue(2);

    priceMinSpinBox = new QSpinBox(this);
    priceMinSpinBox->setRange(0, 1000000);
    priceMinSpinBox->setSpecialValueText(tr("No Min"));

    priceMaxSpinBox = new QSpinBox(this);
    priceMaxSpinBox->setRange(0, 1000000);
    priceMaxSpinBox->setSpecialValueText(tr("No Max"));

    yearMinSpinBox = new QSpinBox(this);
    yearMinSpinBox->setRange(0, 2026);
    yearMinSpinBox->setSpecialValueText(tr("No Min"));

    yearMaxSpinBox = new QSpinBox(this);
    yearMaxSpinBox->setRange(0, 2026);
    yearMaxSpinBox->setSpecialValueText(tr("No Max"));

    detailCheckBox = new QCheckBox(tr("Deep Scrape (Visits each page, slower)"), this);
    showBrowserCheckBox = new QCheckBox(tr("Visible Browser window (Disable headless mode)"), this);

    formLayout->addRow(tr("Car Brand:"), brandInput);
    formLayout->addRow(tr("Pages:"), pagesSpinBox);
    formLayout->addRow(tr("Min Price (€):"), priceMinSpinBox);
    formLayout->addRow(tr("Max Price (€):"), priceMaxSpinBox);
    formLayout->addRow(tr("Min Year:"), yearMinSpinBox);
    formLayout->addRow(tr("Max Year:"), yearMaxSpinBox);
    formLayout->addRow(detailCheckBox);
    formLayout->addRow(showBrowserCheckBox);
    mainLayout->addWidget(filterGroup);

    runButton = new QPushButton(tr("Execute Web Scraper"), this);
    runButton->setStyleSheet("font-weight: bold; padding: 6px; background-color: #2da44e; color: white;");
    mainLayout->addWidget(runButton);

    resultsTableView = new QTableView(this);
    tableModel = new QStandardItemModel(this);
    resultsTableView->setModel(tableModel);
    resultsTableView->setAlternatingRowColors(true);
    resultsTableView->horizontalHeader()->setSectionResizeMode(QHeaderView::Interactive);
    mainLayout->addWidget(resultsTableView);
}

void ScraperWidget::onRunScraperClicked()
{
    QString baseOutputName = "olx_carros.csv";

    // Base path pointing to the unified JuOLXana directory location
    expectedCsvPath = QDir(PROJECT_SOURCE_DIR).absoluteFilePath("../JuOLXana/" + baseOutputName);

    // Absolute path to the Python scraper script inside the JuOLXana folder
    QString scriptPath = QDir(PROJECT_SOURCE_DIR).absoluteFilePath("../JuOLXana/olx_car_scraper.py");

    QStringList arguments;
    arguments << scriptPath;
    arguments << "--output" << QDir(PROJECT_SOURCE_DIR).absoluteFilePath("../JuOLXana/olx_carros");
    arguments << "--formato" << "csv";
    arguments << "--pages" << QString::number(pagesSpinBox->value());

    // --- ALL FILTERS RESTORED AND VERIFIED ---
    if (!brandInput->text().trimmed().isEmpty()) {
        arguments << "--marca" << brandInput->text().trimmed();
    }
    if (priceMinSpinBox->value() > 0) {
        arguments << "--preco-min" << QString::number(priceMinSpinBox->value());
    }
    if (priceMaxSpinBox->value() > 0) {
        arguments << "--preco-max" << QString::number(priceMaxSpinBox->value());
    }
    if (yearMinSpinBox->value() > 0) {
        arguments << "--ano-min" << QString::number(yearMinSpinBox->value());
    }
    if (yearMaxSpinBox->value() > 0) {
        arguments << "--ano-max" << QString::number(yearMaxSpinBox->value());
    }
    if (detailCheckBox->isChecked()) {
        arguments << "--detalhe";
    }
    if (showBrowserCheckBox->isChecked()) {
        arguments << "--no-headless";
    }
    // -----------------------------------------

    runButton->setEnabled(false);
    runButton->setText(tr("Scraping Data Live... Please Wait..."));
    tableModel->clear();

    // Force UTF-8 text streams for the Python process on Windows environment channels
    QProcessEnvironment env = QProcessEnvironment::systemEnvironment();
    env.insert("PYTHONIOENCODING", "utf-8");
    scraperProcess->setProcessEnvironment(env);

#ifdef Q_OS_WIN
    scraperProcess->start("python", arguments);
#else
    scraperProcess->start("python3", arguments);
#endif
}

void ScraperWidget::onScraperFinished(int exitCode, QProcess::ExitStatus exitStatus)
{
    runButton->setEnabled(true);
    runButton->setText(tr("Execute Web Scraper"));

    if (exitStatus == QProcess::CrashExit || exitCode != 0) {
        QMessageBox::critical(this, tr("Process Error"), tr("The script failed. Please verify dependencies."));
        return;
    }

    QString actualCsvPath = QDir(PROJECT_SOURCE_DIR).absoluteFilePath("../JuOLXana/olx_carros.csv");

    if (!QFile::exists(actualCsvPath)) {
        QMessageBox::warning(this, tr("File Not Found"),
                             tr("olx_carros.csv não foi encontrado no JuOLXana."));
        return;
    }

    loadCsvToTable(actualCsvPath); // FIX: Make sure to pass actualCsvPath, NOT expectedCsvPath
}

void ScraperWidget::loadCsvToTable(const QString &filePath)
{
    QFile file(filePath);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) return;

    QTextStream in(&file);
    in.setEncoding(QStringConverter::Utf8);
    bool isHeader = true;

    while (!in.atEnd()) {
        QString line = in.readLine();
        QStringList fields;
        bool inQuotes = false;
        QString currentField = "";

        for (int i = 0; i < line.length(); ++i) {
            QChar ch = line[i];
            if (ch == '"') inQuotes = !inQuotes;
            else if (ch == ',' && !inQuotes) { fields.append(currentField.trimmed()); currentField = ""; }
            else currentField.append(ch);
        }
        fields.append(currentField.trimmed());

        if (isHeader) { tableModel->setHorizontalHeaderLabels(fields); isHeader = false; }
        else {
            QList<QStandardItem*> rowItems;
            for (const QString &field : fields) rowItems.append(new QStandardItem(field));
            tableModel->appendRow(rowItems);
        }
    }
    file.close();
}

void ScraperWidget::readScraperOutput()
{
    // Read raw data bytes from the process streams
    QByteArray stdOutput = scraperProcess->readAllStandardOutput();
    if(!stdOutput.isEmpty()) {
        // Convert the raw UTF-8 byte array to a readable QString
        QString logText = QString::fromUtf8(stdOutput).trimmed();
        // qPrintable removes formatting quote marks from the qDebug stream
        qDebug() << "[Python Log]:\n" << qPrintable(logText);
    }

    QByteArray stdError = scraperProcess->readAllStandardError();
    if(!stdError.isEmpty()) {
        QString errorText = QString::fromUtf8(stdError).trimmed();
        qDebug() << "[Python CRITICAL Error]:\n" << qPrintable(errorText);
    }
}