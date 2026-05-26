#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include <QStackedWidget>
#include "ScraperWidget.h"

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    MainWindow(QWidget *parent = nullptr);
    ~MainWindow();

private slots:
    void switchToScraperView();
    void switchToMainMenuView();
    void onMlClicked();
    void onCheckCarsClicked();

private:
    void setupMainMenuUi();

    QStackedWidget *stackedWidget;
    QWidget *mainMenuWidget;
    ScraperWidget *scraperWidget;

    // Fallback view widgets for your other features
    QWidget *mlWidget;
    QWidget *checkCarsWidget;
};

#endif // MAINWINDOW_H