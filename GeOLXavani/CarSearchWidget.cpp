#include "CarSearchWidget.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGroupBox>
#include <QLabel>
#include <QHeaderView>
#include <QFile>
#include <QTextStream>
#include <QDir>
#include <QMessageBox>

CarSearchWidget::CarSearchWidget(QWidget *parent) : QWidget(parent)
{
    setupUi();
}

CarSearchWidget::~CarSearchWidget() {}

void CarSearchWidget::setupUi()
{
    QVBoxLayout *mainLayout = new QVBoxLayout(this);

    QHBoxLayout *headerLayout = new QHBoxLayout();
    backButton = new QPushButton(tr("← Back to Training Console"), this);
    headerLayout->addWidget(backButton);
    headerLayout->addStretch();

    QLabel *titleLabel = new QLabel(tr("Local Database Search Engine"), this);
    titleLabel->setStyleSheet("font-size: 16px; font-weight: bold;");
    headerLayout->addWidget(titleLabel);
    headerLayout->addStretch();
    mainLayout->addLayout(headerLayout);

    QGroupBox *searchGroup = new QGroupBox(tr("Filters"), this);
    QHBoxLayout *searchLayout = new QHBoxLayout(searchGroup);

    searchFieldCombo = new QComboBox(this);
    searchFieldCombo->addItem(tr("All Fields"));

    searchLineEdit = new QLineEdit(this);
    searchLineEdit->setPlaceholderText(tr("Search entry keyword..."));

    searchButton = new QPushButton(tr("Filter"), this);
    searchButton->setStyleSheet("background-color: #2da44e; color: white; padding: 4px 12px;");

    searchLayout->addWidget(new QLabel(tr("Field:"), this));
    searchLayout->addWidget(searchFieldCombo);
    searchLayout->addWidget(searchLineEdit, 1);
    searchLayout->addWidget(searchButton);
    mainLayout->addWidget(searchGroup);

    resultsTableView = new QTableView(this);
    tableModel = new QStandardItemModel(this);
    resultsTableView->setModel(tableModel);
    resultsTableView->setAlternatingRowColors(true);
    resultsTableView->horizontalHeader()->setSectionResizeMode(QHeaderView::Stretch);
    mainLayout->addWidget(resultsTableView);

    connect(searchButton, &QPushButton::clicked, this, &CarSearchWidget::onSearchClicked);
    connect(searchLineEdit, &QLineEdit::returnPressed, this, &CarSearchWidget::onSearchClicked);
    connect(backButton, &QPushButton::clicked, this, &CarSearchWidget::backToTrainingRequested);
}

void CarSearchWidget::loadDataset()
{
    QString csvPath = QDir(PROJECT_SOURCE_DIR).absoluteFilePath("../JuOLXana/olx_carros.csv");
    if (!QFile::exists(csvPath)) return;

    QFile file(csvPath);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) return;

    originalData.clear();
    headers.clear();

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
            else if (ch == ',' && !inQuotes) {
                fields.append(currentField.trimmed());
                currentField = "";
            } else {
                currentField.append(ch);
            }
        }
        fields.append(currentField.trimmed());

        if (isHeader) {
            headers = fields;
            searchFieldCombo->clear();
            searchFieldCombo->addItem(tr("All Fields"));
            for (const QString &h : headers) searchFieldCombo->addItem(h);
            isHeader = false;
        } else {
            if(!fields.isEmpty() && !fields[0].isEmpty()) {
                originalData.append(fields);
            }
        }
    }
    file.close();
    filterTable();
}

void CarSearchWidget::onSearchClicked()
{
    filterTable();
}

void CarSearchWidget::filterTable()
{
    tableModel->clear();
    tableModel->setHorizontalHeaderLabels(headers);

    QString filterText = searchLineEdit->text().trimmed().toLower();
    int searchIndex = searchFieldCombo->currentIndex() - 1;

    for (const QStringList &row : originalData) {
        bool match = false;
        if (filterText.isEmpty()) {
            match = true;
        } else if (searchIndex == -1) {
            for (const QString &cell : row) {
                if (cell.toLower().contains(filterText)) {
                    match = true;
                    break;
                }
            }
        } else if (searchIndex < row.size()) {
            if (row[searchIndex].toLower().contains(filterText)) match = true;
        }

        if (match) {
            QList<QStandardItem*> items;
            for (const QString &cell : row) items.append(new QStandardItem(cell));
            tableModel->appendRow(items);
        }
    }
}