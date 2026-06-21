#include "MainWindow.h"
#include "ScraperWidget.h"
#include "MlWidget.h"
#include "TrainingWidget.h"
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

    // Inicialização segura dos componentes
    setupMainMenuUi();
    scraperWidget = new ScraperWidget(this);
    mlWidget = new MlWidget(this);
    checkCarsWidget = new TrainingWidget(this);

    // Registo ordenado no index do QStackedWidget
    stackedWidget->addWidget(mainMenuWidget);     // Index 0
    stackedWidget->addWidget(scraperWidget);      // Index 1
    stackedWidget->addWidget(mlWidget);           // Index 2
    stackedWidget->addWidget(checkCarsWidget);    // Index 3

    // Conexões de roteamento de interface
    connect(scraperWidget, &ScraperWidget::backToMainMenuRequested, this, &MainWindow::switchToMainMenuView);
    connect(mlWidget, &MlWidget::backToMainMenuRequested, this, &MainWindow::switchToMainMenuView);
    connect(checkCarsWidget, &TrainingWidget::backToMainMenuRequested, this, &MainWindow::switchToMainMenuView);
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

    QString btnStyle = "font-size: 14px; padding: 12px; font-weight: 500; text-align: left; padding-left: 20px;";
    btnScrape->setStyleSheet(btnStyle);
    btnMl->setStyleSheet(btnStyle);
    btnCheck->setStyleSheet(btnStyle);

    menuButtonLayout->addWidget(btnScrape);
    menuButtonLayout->addWidget(btnMl);
    menuButtonLayout->addWidget(btnCheck);
    layout->addLayout(menuButtonLayout);
    layout->addStretch();

    connect(btnScrape, &QPushButton::clicked, this, &MainWindow::switchToScraperView);
    connect(btnMl, &QPushButton::clicked, this, &MainWindow::onMlClicked);
    connect(btnCheck, &QPushButton::clicked, this, &MainWindow::onCheckCarsClicked);
}

void MainWindow::switchToScraperView() { stackedWidget->setCurrentIndex(1); }
void MainWindow::switchToMainMenuView() { stackedWidget->setCurrentIndex(0); }

void MainWindow::onCheckCarsClicked()
{
    stackedWidget->setCurrentIndex(3);
}

void MainWindow::onMlClicked()
{
    stackedWidget->setCurrentIndex(2);
}