#include "MainWindow.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QPushButton>
#include <QLabel>
#include <QMessageBox>

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
{
    resize(950, 700);
    setWindowTitle(tr("GeOLXavani Platform Workspace"));

    stackedWidget = new QStackedWidget(this);
    setCentralWidget(stackedWidget);

    // Initialize our views
    setupMainMenuUi();
    scraperWidget = new ScraperWidget(this);

    // Placeholders for your upcoming features
    mlWidget = new QWidget(this);
    checkCarsWidget = new QWidget(this);

    // Register all subsystems inside our content stack switcher
    stackedWidget->addWidget(mainMenuWidget);     // Index 0
    stackedWidget->addWidget(scraperWidget);      // Index 1
    stackedWidget->addWidget(mlWidget);           // Index 2
    stackedWidget->addWidget(checkCarsWidget);    // Index 3

    // Listen to the back button events from the modules
    connect(scraperWidget, &ScraperWidget::backToMainMenuRequested, this, &MainWindow::switchToMainMenuView);
}

MainWindow::~MainWindow() {}

void MainWindow::setupMainMenuUi()
{
    mainMenuWidget = new QWidget(this);
    QVBoxLayout *layout = new QVBoxLayout(mainMenuWidget);

    QLabel *title = new QLabel(tr("Welcome to GeOLXavani Engine"), mainMenuWidget);
    title->setAlignment(Qt::AlignCenter);
    title->setStyleSheet("font-size: 20px; font-weight: bold; margin: 20px; color: #2c3e50;");
    layout->addWidget(title);

    QVBoxLayout *menuButtonLayout = new QVBoxLayout();
    menuButtonLayout->setSpacing(15);
    menuButtonLayout->setContentsMargins(100, 20, 100, 40);

    QPushButton *btnScrape = new QPushButton(tr("🔍 Run Webscraping (OLX)"), mainMenuWidget);
    QPushButton *btnMl = new QPushButton(tr("🤖 Machine Learning Predictive Models"), mainMenuWidget);
    QPushButton *btnCheck = new QPushButton(tr("🚗 Check & Evaluate Cars Data"), mainMenuWidget);

    // Apply some styling to your main landing buttons
    QString btnStyle = "font-size: 14px; padding: 12px; font-weight: 500; text-align: left; padding-left: 20px;";
    btnScrape->setStyleSheet(btnStyle);
    btnMl->setStyleSheet(btnStyle);
    btnCheck->setStyleSheet(btnStyle);

    menuButtonLayout->addWidget(btnScrape);
    menuButtonLayout->addWidget(btnMl);
    menuButtonLayout->addWidget(btnCheck);
    layout->addLayout(menuButtonLayout);
    layout->addStretch();

    // Event routing connections
    connect(btnScrape, &QPushButton::clicked, this, &MainWindow::switchToScraperView);
    connect(btnMl, &QPushButton::clicked, this, &MainWindow::onMlClicked);
    connect(btnCheck, &QPushButton::clicked, this, &MainWindow::onCheckCarsClicked);
}

void MainWindow::switchToScraperView() { stackedWidget->setCurrentIndex(1); }
void MainWindow::switchToMainMenuView() { stackedWidget->setCurrentIndex(0); }

void MainWindow::onMlClicked()
{
    QMessageBox::information(this, tr("ML Module"), tr("This opens your Machine Learning view window later!"));
}

void MainWindow::onCheckCarsClicked()
{
    QMessageBox::information(this, tr("Data Viewer"), tr("This opens your Check Cars view window later!"));
}