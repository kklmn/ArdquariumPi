function state_change(checkbox, delay=500){
    if(checkbox.checked){
//        alert('Checkbox ' + checkbox.name + ' has been ticked!');
        var state = 1;
    }
    else{
//        alert('Checkbox ' + checkbox.name + ' has been unticked!');
        var state = 0;
    }
    state_set(checkbox.id, state, delay);
}

function state_set(name, state, delay=500, how="Manually switched"){
    var data = {"pin": name, "state": state, "how": how};
//    alert('pin ' + pin + ' state ' + state);
    fetch("/", {method: "POST", body: JSON.stringify(data)});
    setTimeout(function(){location.reload(true);}, delay);
}

function thermostat_state(checkbox, delay=500){
    if(checkbox.checked)
        var state = 1;
    else
        var state = 0;
    var data = {"thermostat": 1, "state": state};
    fetch("/", {method: "POST", body: JSON.stringify(data)});
    setTimeout(function(){location.reload(true);}, delay);
}

function time_range_change(timebutton, delay=500){
    var data = {"timedelta": timebutton.id};
//    alert('Timebutton ' + timebutton.id + ' has been clcked!');
    fetch("/", {method: "POST", body: JSON.stringify(data)});
    setTimeout(function(){location.reload(true);}, delay);
}

function y_range_change(timebutton, delay=500){
    var data = {"yrange": timebutton.id};
//    alert('Timebutton ' + timebutton.id + ' has been clcked!');
    fetch("/", {method: "POST", body: JSON.stringify(data)});
    setTimeout(function(){location.reload(true);}, delay);
}

function set_countdown(countdownTime){
    if (countdownTime <= 0)
        return;

    var x = setInterval(function() {
      var minutes = Math.floor(countdownTime / 60);
      var seconds = countdownTime % 60;

      if (countdownTime < 60) {
        document.getElementById("countdown").innerHTML = seconds + "s ";
      }
      else {
        document.getElementById("countdown").innerHTML = minutes + "m " + 
          ((seconds < 10)?"0":"") + seconds + "s";
      }  

      // When the count down is over:
      if (countdownTime <= 0) {
        clearInterval(x);
        document.getElementById("countdown").innerHTML = " ";
        state_set("feeding", 0, 750, "Timer-switched");
      }
      countdownTime -= 1;
    }, 1000);
}

function make_current_date(){
    // For todays date;
    Date.prototype.today = function () { 
        return this.getFullYear() + "/" +
        (((this.getMonth()+1) < 10)?"0":"") + (this.getMonth()+1) + "/" +
        ((this.getDate() < 10)?"0":"") + this.getDate();
    }
    // For the time now
    Date.prototype.timeNow = function () {
         return ((this.getHours() < 10)?"0":"") + this.getHours() + ":" +
         ((this.getMinutes() < 10)?"0":"") + this.getMinutes() + ":" +
         ((this.getSeconds() < 10)?"0":"") + this.getSeconds();
    }
    var datetime = new Date().today() + "\n" + new Date().timeNow();
    document.getElementById("currentDate").innerHTML = datetime;
}
