#include "MainWindow.h"
#include <QFileDialog>
#include <QMessageBox>
#include <QCoreApplication>

MainWindow::MainWindow(QWidget *parent) : QMainWindow(parent) {
    setWindowTitle("OLX Car Analyzer Platform");
    resize(450, 400);

    stackedWidget = new QStackedWidget(this);
    setCentralWidget(stackedWidget);

    // Build the views
    createMainMenu();
    createTrainModelView();
    createCheckValueView();

    // Add them to the stack
    stackedWidget->addWidget(mainMenuWidget);     // Index 0
    stackedWidget->addWidget(trainModelWidget);    // Index 1
    stackedWidget->addWidget(checkValueWidget);    // Index 2

    // Start at the Main Menu
    showMainMenu();
}

MainWindow::~MainWindow() {}

void MainWindow::createMainMenu() {
    mainMenuWidget = new QWidget();
    QVBoxLayout *layout = new QVBoxLayout(mainMenuWidget);
    layout->setSpacing(15);
    layout->setContentsMargins(40, 40, 40, 40);

    QLabel *titleLabel = new QLabel("Vehicle ML Suite", mainMenuWidget);
    titleLabel->setAlignment(Qt::AlignCenter);
    QFont titleFont = titleLabel->font();
    titleFont.setPointSize(16);
    titleFont.setBold(true);
    titleLabel->setFont(titleFont);
    layout->addWidget(titleLabel);

    QPushButton *btnScrape = new QPushButton("Run Webscraping (OLX)", mainMenuWidget);
    QPushButton *btnTrain = new QPushButton("Train ML Model", mainMenuWidget);
    QPushButton *btnCheck = new QPushButton("Check Car Value", mainMenuWidget);
    QPushButton *btnQuit = new QPushButton("Quit Application", mainMenuWidget);

    layout->addWidget(btnScrape);
    layout->addWidget(btnTrain);
    layout->addWidget(btnCheck);
    layout->addSpacing(10);
    layout->addWidget(btnQuit);

    // Connect Main Menu Buttons to Actions/Navigation
    connect(btnScrape, &QPushButton::clicked, this, &MainWindow::runWebScraper);
    connect(btnTrain, &QPushButton::clicked, this, &MainWindow::showTrainModelView);
    connect(btnCheck, &QPushButton::clicked, this, &MainWindow::showCheckValueView);
    connect(btnQuit, &QPushButton::clicked, qApp, &QCoreApplication::quit);
}

void MainWindow::createTrainModelView() {
    trainModelWidget = new QWidget();
    QVBoxLayout *layout = new QVBoxLayout(trainModelWidget);

    QLabel *label = new QLabel("<h2>Train Model Dataset Setup</h2>");
    layout->addWidget(label);

    QHBoxLayout *fileLayout = new QHBoxLayout();
    datasetPathInput = new QLineEdit();
    datasetPathInput->setPlaceholderText("Path to scraped CSV/JSON file...");
    QPushButton *btnBrowse = new QPushButton("Browse File");
    fileLayout->addWidget(datasetPathInput);
    fileLayout->addWidget(btnBrowse);
    layout->addLayout(fileLayout);

    QPushButton *btnExecuteTrain = new QPushButton("Start Training Loop");
    QPushButton *btnBack = new QPushButton("Back to Menu");
    layout->addWidget(btnExecuteTrain);
    layout->addStretch();
    layout->addWidget(btnBack);

    // File Dialog Browser Connection
    connect(btnBrowse, &QPushButton::clicked, this, [=]() {
        QString filePath = QFileDialog::getOpenFileName(this, "Select Dataset", "", "Data Files (*.csv *.json)");
        if (!filePath.isEmpty()) datasetPathInput->setText(filePath);
    });

    connect(btnExecuteTrain, &QPushButton::clicked, this, &MainWindow::handleTrainModel);
    connect(btnBack, &QPushButton::clicked, this, &MainWindow::showMainMenu);
}

void MainWindow::createCheckValueView() {
    checkValueWidget = new QWidget();
    QVBoxLayout *layout = new QVBoxLayout(checkValueWidget);

    layout->addWidget(new QLabel("<h2>Car Evaluation Features</h2>"));

    // Input fields layout
    brandInput = new QLineEdit(); brandInput->setPlaceholderText("e.g., BMW");
    modelInput = new QLineEdit(); modelInput->setPlaceholderText("e.g., 320d");
    yearInput = new QLineEdit(); yearInput->setPlaceholderText("e.g., 2019");
    kmInput = new QLineEdit(); kmInput->setPlaceholderText("e.g., 140000");

    layout->addWidget(new QLabel("Brand:")); layout->addWidget(brandInput);
    layout->addWidget(new QLabel("Model:")); layout->addWidget(modelInput);
    layout->addWidget(new QLabel("Year:")); layout->addWidget(yearInput);
    layout->addWidget(new QLabel("Kilometers:")); layout->addWidget(kmInput);

    priceResultLabel = new QLabel("Estimated Price: -- €");
    priceResultLabel->setStyleSheet("font-size: 14px; font-weight: bold; color: green; margin: 10px 0;");
    layout->addWidget(priceResultLabel);

    QPushButton *btnPredict = new QPushButton("Predict Value via Python");
    QPushButton *btnBack = new QPushButton("Back to Menu");
    layout->addWidget(btnPredict);
    layout->addStretch();
    layout->addWidget(btnBack);

    connect(btnPredict, &QPushButton::clicked, this, &MainWindow::handleCheckPrice);
    connect(btnBack, &QPushButton::clicked, this, &MainWindow::showMainMenu);
}

// Navigation implementation
void MainWindow::showMainMenu() { stackedWidget->setCurrentIndex(0); }
void MainWindow::showTrainModelView() { stackedWidget->setCurrentIndex(1); }
void MainWindow::showCheckValueView() { stackedWidget->setCurrentIndex(2); }

// Executing the Webscraper in the command line terminal
void MainWindow::runWebScraper() {
    QProcess *process = new QProcess(this);

    // Assumes webcar.py lives in the same folder execution directory
    QString scriptPath = QCoreApplication::applicationDirPath() + "/webcar.py";

    // Windows OS: Opens cmd.exe, runs Python script inside it and stays open
#if defined(Q_OS_WIN)
    QString program = "cmd.exe";
    QStringList arguments;
    arguments << "/c" << "start" << "cmd.exe" << "/k" << "python" << scriptPath;
#elif defined(Q_OS_MAC)
    // macOS: Triggers a native Terminal window to run Python
    QString program = "osascript";
    QStringList arguments;
    arguments << "-e" << QString("tell application \"Terminal\" to do script \"python3 '%1'\"").arg(scriptPath);
#else
    // Linux OS: Launches default gnome-terminal (or similar standard desktop terminal setup)
    QString program = "gnome-terminal";
    QStringList arguments;
    arguments << "--" << "python3" << scriptPath;
#endif

    process->start(program, arguments);
}

void MainWindow::handleTrainModel() {
    if (datasetPathInput->text().isEmpty()) {
        QMessageBox::warning(this, "Missing File", "Please choose a valid dataset file first!");
        return;
    }
    // Placeholder message box. You will attach your future execution process here.
    QMessageBox::information(this, "ML Engine", "Dataset linked! Ready to trigger python model training pipeline.");
}

void MainWindow::handleCheckPrice() {
    // Basic structural validation check
    if(brandInput->text().isEmpty() || yearInput->text().isEmpty()) {
        QMessageBox::warning(this, "Missing Fields", "Please supply at least a Brand and Year for evaluation.");
        return;
    }

    // Future expansion point: capture text() from lines, parse into json/arguments, call Python via QProcess.
    priceResultLabel->setText(QString("Estimated Price: Calculating via ML script..."));
}