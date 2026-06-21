#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include <QStackedWidget>

// Forward Declarations: Dizemos ao compilador que estas classes existem,
// sem precisar de incluir os ficheiros .h completos aqui dentro.
class ScraperWidget;
class MlWidget;
class TrainingWidget;

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

    // Ponteiros com os tipos exatos e corretos
    ScraperWidget *scraperWidget;
    MlWidget *mlWidget;
    TrainingWidget *checkCarsWidget;
};

#endif // MAINWINDOW_H