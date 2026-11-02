<#
.SYNOPSIS
    TV-Safe, Hardware-Accelerated GameStation Console Overlay for Windows.
    Displays modern console toasts and error screens using built-in Windows WPF.
.PARAMETER Type
    READING, LAUNCH_PS1, LAUNCH_PS2, ERROR, WARNING, CLOSE
#>
param(
    [string]$Type = "LAUNCH_PS2",
    [string]$Title = "PlayStation 2 Disc Detected",
    [string]$Subtitle = "Final Fantasy X",
    [string]$Serial = "SLUS-20062",
    [string]$Message = "",
    [double]$DurationSeconds = 3.5,
    [switch]$CloseExisting
)

# Mutex/pipe file to track and replace active overlay
$stateFile = Join-Path $env:TEMP "psconsole_overlay_state.pid"

if ($CloseExisting -or $Type -eq "CLOSE") {
    if (Test-Path $stateFile) {
        $oldPid = Get-Content $stateFile -ErrorAction SilentlyContinue
        if ($oldPid) {
            Stop-Process -Id $oldPid -Force -ErrorAction SilentlyContinue
        }
        Remove-Item $stateFile -Force -ErrorAction SilentlyContinue
    }
    if ($Type -eq "CLOSE") { exit 0 }
}

# Kill previous overlay instance so toasts replace smoothly
if (Test-Path $stateFile) {
    $oldPid = Get-Content $stateFile -ErrorAction SilentlyContinue
    if ($oldPid) {
        Stop-Process -Id $oldPid -Force -ErrorAction SilentlyContinue
    }
}
$PID | Set-Content $stateFile -Force

# Load WPF
Add-Type -AssemblyName PresentationFramework, PresentationCore, WindowsBase

[xml]$xaml = @"
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="PSConsoleOverlay"
        WindowStyle="None"
        AllowsTransparency="True"
        Background="Transparent"
        Topmost="True"
        ShowInTaskbar="False"
        SizeToContent="WidthAndHeight"
        Opacity="0">
    <Border Name="MainBorder" CornerRadius="14" Margin="20" Padding="24,18"
            BorderThickness="2" SnapsToDevicePixels="True">
        <Border.Effect>
            <DropShadowEffect BlurRadius="25" ShadowDepth="4" Opacity="0.65" Color="#000000"/>
        </Border.Effect>
        <Grid Name="ContentGrid">
            <Grid.ColumnDefinitions>
                <ColumnDefinition Width="Auto"/>
                <ColumnDefinition Width="*"/>
            </Grid.ColumnDefinitions>

            <!-- Icon / Disc Indicator -->
            <Canvas Name="IconCanvas" Width="52" Height="52" Margin="0,0,20,0" VerticalAlignment="Center">
                <Ellipse Width="50" Height="50" Stroke="#0070D1" StrokeThickness="3" Fill="#10192D"/>
                <Ellipse Width="18" Height="18" Canvas.Left="16" Canvas.Top="16" Stroke="#00A9E0" StrokeThickness="2" Fill="#090D16"/>
                <Path Name="IconGlyph" Fill="#00A9E0" Canvas.Left="20" Canvas.Top="14"
                      Data="M 0,0 L 10,0 L 5,10 Z"/>
            </Canvas>

            <!-- Text Content -->
            <StackPanel Grid.Column="1" VerticalAlignment="Center" MinWidth="340" MaxWidth="620">
                <StackPanel Orientation="Horizontal" Margin="0,0,0,4">
                    <Border Name="BadgeBorder" CornerRadius="5" Padding="7,2" Margin="0,0,10,0" Background="#00439C">
                        <TextBlock Name="BadgeText" Text="PLAYSTATION" FontWeight="Bold" FontSize="11" Foreground="#FFFFFF"/>
                    </Border>
                    <TextBlock Name="SerialText" Text="[SLUS-20062]" FontSize="12" Foreground="#7E93B0" VerticalAlignment="Center"/>
                </StackPanel>

                <TextBlock Name="TitleText" Text="Final Fantasy X" FontSize="20" FontWeight="Bold" Foreground="#FFFFFF"
                           TextWrapping="Wrap" Margin="0,0,0,3"/>

                <TextBlock Name="SubText" Text="Starting disc in fullscreen..." FontSize="13" Foreground="#B0C4DE"
                           TextWrapping="Wrap"/>
            </StackPanel>
        </Grid>
    </Border>
</Window>
"@

$reader = New-Object System.Xml.XmlNodeReader $xaml
$window = [Windows.Markup.XamlReader]::Load($reader)

# Elements
$mainBorder = $window.FindName("MainBorder")
$badgeBorder = $window.FindName("BadgeBorder")
$badgeText = $window.FindName("BadgeText")
$serialText = $window.FindName("SerialText")
$titleText = $window.FindName("TitleText")
$subText = $window.FindName("SubText")

# Set Theme Styles based on Type
switch -Regex ($Type) {
    "READING" {
        $mainBorder.Background = [Windows.Media.SolidColorBrush][Windows.Media.Color]::FromArgb(235, 10, 16, 28)
        $mainBorder.BorderBrush = [Windows.Media.SolidColorBrush][Windows.Media.Color]::FromRgb(0, 112, 209)
        $badgeBorder.Background = [Windows.Media.SolidColorBrush][Windows.Media.Color]::FromRgb(0, 67, 156)
        $badgeText.Text = "OPTICAL DRIVE"
        $serialText.Text = "BUSY"
        $titleText.Text = if ($Title) { $Title } else { "Reading Disc..." }
        $subText.Text = if ($Subtitle) { $Subtitle } else { "Checking PlayStation format and Table of Contents" }
    }
    "LAUNCH_PS1" {
        $mainBorder.Background = [Windows.Media.SolidColorBrush][Windows.Media.Color]::FromArgb(245, 12, 18, 32)
        $mainBorder.BorderBrush = [Windows.Media.SolidColorBrush][Windows.Media.Color]::FromRgb(0, 112, 209)
        $badgeBorder.Background = [Windows.Media.SolidColorBrush][Windows.Media.Color]::FromRgb(0, 75, 165)
        $badgeText.Text = "PLAYSTATION 1"
        $serialText.Text = if ($Serial) { "[$Serial]" } else { "" }
        $titleText.Text = $Title
        $subText.Text = if ($Subtitle) { $Subtitle } else { "Starting game in DuckStation..." }
    }
    "LAUNCH_PS2" {
        $mainBorder.Background = [Windows.Media.SolidColorBrush][Windows.Media.Color]::FromArgb(245, 8, 14, 26)
        $mainBorder.BorderBrush = [Windows.Media.SolidColorBrush][Windows.Media.Color]::FromRgb(0, 140, 255)
        $badgeBorder.Background = [Windows.Media.SolidColorBrush][Windows.Media.Color]::FromRgb(0, 100, 210)
        $badgeText.Text = "PLAYSTATION 2"
        $serialText.Text = if ($Serial) { "[$Serial]" } else { "" }
        $titleText.Text = $Title
        $subText.Text = if ($Subtitle) { $Subtitle } else { "Starting game in PCSX2..." }
    }
    "ERROR|UNSUPPORTED|UNREADABLE" {
        $mainBorder.Background = [Windows.Media.SolidColorBrush][Windows.Media.Color]::FromArgb(248, 28, 12, 16)
        $mainBorder.BorderBrush = [Windows.Media.SolidColorBrush][Windows.Media.Color]::FromRgb(220, 53, 69)
        $badgeBorder.Background = [Windows.Media.SolidColorBrush][Windows.Media.Color]::FromRgb(180, 40, 50)
        $badgeText.Text = "DISC ERROR"
        $serialText.Text = ""
        $titleText.Text = if ($Title) { $Title } else { "Unsupported Disc" }
        $subText.Text = if ($Message) { $Message } else { "Please eject the disc. Press (B) to dismiss." }
        $subText.Foreground = [Windows.Media.SolidColorBrush][Windows.Media.Color]::FromRgb(255, 180, 180)
    }
    Default {
        $mainBorder.Background = [Windows.Media.SolidColorBrush][Windows.Media.Color]::FromArgb(240, 10, 16, 28)
        $mainBorder.BorderBrush = [Windows.Media.SolidColorBrush][Windows.Media.Color]::FromRgb(0, 112, 209)
        $badgeText.Text = "PLAYSTATION"
        $titleText.Text = $Title
        $subText.Text = $Subtitle
    }
}

# Position overlay in TV-safe lower-center of primary screen
$screenW = [System.Windows.SystemParameters]::PrimaryScreenWidth
$screenH = [System.Windows.SystemParameters]::PrimaryScreenHeight

$window.Left = ($screenW / 2) - 260
$window.Top = $screenH - 180

# Fade-in animation
$fadeIn = New-Object Windows.Media.Animation.DoubleAnimation(0.0, 1.0, (New-Object Windows.Duration([TimeSpan]::FromMilliseconds(220))))
$window.BeginAnimation([Windows.UIElement]::OpacityProperty, $fadeIn)

# Dismiss on click or key
$window.Add_MouseDown({ $window.Close() })
$window.Add_KeyDown({ $window.Close() })

# Auto dismiss timer
$timer = New-Object Windows.Threading.DispatcherTimer
$timer.Interval = [TimeSpan]::FromSeconds($DurationSeconds)
$timer.Add_Tick({
    $timer.Stop()
    $fadeOut = New-Object Windows.Media.Animation.DoubleAnimation(1.0, 0.0, (New-Object Windows.Duration([TimeSpan]::FromMilliseconds(250))))
    $fadeOut.Add_Completed({ $window.Close() })
    $window.BeginAnimation([Windows.UIElement]::OpacityProperty, $fadeOut)
})
$timer.Start()

$null = $window.ShowDialog()
Remove-Item $stateFile -Force -ErrorAction SilentlyContinue
